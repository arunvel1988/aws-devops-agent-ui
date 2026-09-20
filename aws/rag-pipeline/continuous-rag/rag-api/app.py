import os
import re
import time
import hashlib
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document


# ============================================================
# CONFIG
# ============================================================

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "company_knowledge")

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"
)

WATCH_DIR = Path(
    os.getenv("WATCH_DIR", "/data/documents")
)

TOP_K = int(os.getenv("TOP_K", "5"))

CHUNK_SIZE = int(
    os.getenv("CHUNK_SIZE", "800")
)

CHUNK_OVERLAP = int(
    os.getenv("CHUNK_OVERLAP", "120")
)

SCAN_INTERVAL = int(
    os.getenv("SCAN_INTERVAL", "5")
)

SUPPORTED = {
    ".txt",
    ".md",
    ".pdf",
    ".docx"
}


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Continuous RAG API",
    version="2.0.0"
)

qdrant = QdrantClient(
    url=QDRANT_URL
)

embedder = SentenceTransformer(
    MODEL_NAME
)


# ============================================================
# QDRANT
# ============================================================

def wait_for_qdrant():

    print("[QDRANT] Waiting for Qdrant...")

    for attempt in range(60):

        try:

            qdrant.get_collections()

            print("[QDRANT] Connected")

            return

        except Exception:

            print(
                f"[QDRANT] Not ready. Attempt {attempt + 1}/60"
            )

            time.sleep(2)

    raise RuntimeError(
        "Qdrant did not become ready"
    )


def ensure_collection():

    wait_for_qdrant()

    dim = embedder.get_embedding_dimension()

    names = [
        c.name
        for c in qdrant.get_collections().collections
    ]

    if COLLECTION not in names:

        print(
            f"[QDRANT] Creating collection: {COLLECTION}"
        )

        qdrant.create_collection(

            collection_name=COLLECTION,

            vectors_config=models.VectorParams(

                size=dim,

                distance=models.Distance.COSINE

            )
        )

    else:

        print(
            f"[QDRANT] Collection already exists: {COLLECTION}"
        )


# ============================================================
# DOCUMENT READING
# ============================================================

def read_document(path: Path) -> str:

    extension = path.suffix.lower()

    if extension in {".txt", ".md"}:

        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    if extension == ".pdf":

        reader = PdfReader(
            str(path)
        )

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:

                pages.append(text)

        return "\n".join(pages)

    if extension == ".docx":

        doc = Document(
            str(path)
        )

        return "\n".join(
            p.text
            for p in doc.paragraphs
        )

    return ""


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize(text: str) -> str:

    text = re.sub(
        r"\r\n?",
        "\n",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# CHUNKING
# ============================================================

def chunk_text(text: str):

    text = normalize(text)

    if not text:

        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            len(text),
            start + CHUNK_SIZE
        )

        chunk = text[start:end].strip()

        if chunk:

            chunks.append(chunk)

        if end >= len(text):

            break

        start = max(
            end - CHUNK_OVERLAP,
            start + 1
        )

    return chunks


# ============================================================
# DOCUMENT HASH
# ============================================================

def calculate_hash(path: Path):

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            data = f.read(1024 * 1024)

            if not data:

                break

            sha256.update(data)

    return sha256.hexdigest()


# ============================================================
# DOCUMENT ID
# ============================================================

def document_id(relative_path: str):

    return hashlib.sha256(
        relative_path.encode()
    ).hexdigest()


def stable_point_id(
    document_hash: str,
    chunk_index: int
):

    raw = hashlib.sha256(
        f"{document_hash}:{chunk_index}".encode()
    ).hexdigest()[:15]

    return int(raw, 16) % (
        2**63 - 1
    )


# ============================================================
# DELETE DOCUMENT FROM QDRANT
# ============================================================

def delete_document(relative_path: str):

    try:

        qdrant.delete(

            collection_name=COLLECTION,

            points_selector=models.FilterSelector(

                filter=models.Filter(

                    must=[

                        models.FieldCondition(

                            key="path",

                            match=models.MatchValue(
                                value=relative_path
                            )

                        )

                    ]

                )

            )

        )

        print(
            f"[DELETE] Removed from Qdrant: "
            f"{relative_path}"
        )

    except Exception as e:

        print(
            f"[DELETE ERROR] {relative_path}: {e}"
        )


# ============================================================
# INGEST DOCUMENT
# ============================================================

def ingest_file(path: Path):

    if not path.exists():

        return

    if path.suffix.lower() not in SUPPORTED:

        return

    try:

        relative_path = str(
            path.relative_to(WATCH_DIR)
        )

        print(
            f"[PROCESSING] {relative_path}"
        )

        # ----------------------------------------------------
        # Calculate document hash
        # ----------------------------------------------------

        doc_hash = calculate_hash(
            path
        )

        # ----------------------------------------------------
        # Check whether same document/version
        # already exists in Qdrant
        # ----------------------------------------------------

        existing = qdrant.scroll(

            collection_name=COLLECTION,

            scroll_filter=models.Filter(

                must=[

                    models.FieldCondition(

                        key="path",

                        match=models.MatchValue(
                            value=relative_path
                        )

                    ),

                    models.FieldCondition(

                        key="document_hash",

                        match=models.MatchValue(
                            value=doc_hash
                        )

                    )

                ]

            ),

            limit=1,

            with_payload=True,

            with_vectors=False

        )

        if existing[0]:

            print(
                f"[SKIP] Unchanged: "
                f"{relative_path}"
            )

            return

        # ----------------------------------------------------
        # Read document
        # ----------------------------------------------------

        text = read_document(
            path
        )

        if not text.strip():

            print(
                f"[SKIP] Empty document: "
                f"{relative_path}"
            )

            return

        # ----------------------------------------------------
        # Delete previous version
        # ----------------------------------------------------

        delete_document(
            relative_path
        )

        # ----------------------------------------------------
        # Chunk
        # ----------------------------------------------------

        chunks = chunk_text(
            text
        )

        if not chunks:

            return

        print(
            f"[CHUNK] {relative_path}: "
            f"{len(chunks)} chunks"
        )

        # ----------------------------------------------------
        # Generate embeddings
        # ----------------------------------------------------

        vectors = embedder.encode(

            chunks,

            normalize_embeddings=True

        ).tolist()

        # ----------------------------------------------------
        # Create Qdrant points
        # ----------------------------------------------------

        points = []

        updated_at = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime()
        )

        for index, (
            chunk,
            vector
        ) in enumerate(
            zip(chunks, vectors)
        ):

            points.append(

                models.PointStruct(

                    id=stable_point_id(
                        doc_hash,
                        index
                    ),

                    vector=vector,

                    payload={

                        "source": path.name,

                        "path": relative_path,

                        "document_hash": doc_hash,

                        "chunk_index": index,

                        "text": chunk,

                        "updated_at": updated_at

                    }

                )

            )

        # ----------------------------------------------------
        # Store in Qdrant
        # ----------------------------------------------------

        qdrant.upsert(

            collection_name=COLLECTION,

            points=points

        )

        print(
            f"[INGESTED] {relative_path} "
            f"-> {len(points)} chunks"
        )

    except Exception as e:

        print(
            f"[ERROR] {path}: {e}"
        )


# ============================================================
# CONTINUOUS SCANNER
# ============================================================

def scan_documents():

    WATCH_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    current_files = set()

    for path in WATCH_DIR.rglob("*"):

        if not path.is_file():

            continue

        if path.suffix.lower() not in SUPPORTED:

            continue

        current_files.add(
            str(
                path.relative_to(WATCH_DIR)
            )
        )

        ingest_file(
            path
        )

    return current_files


def cleanup_deleted_documents():

    # Get indexed documents from Qdrant

    offset = None

    indexed_paths = set()

    while True:

        records, offset = qdrant.scroll(

            collection_name=COLLECTION,

            limit=100,

            offset=offset,

            with_payload=True,

            with_vectors=False

        )

        for point in records:

            payload = point.payload or {}

            path = payload.get(
                "path"
            )

            if path:

                indexed_paths.add(
                    path
                )

        if offset is None:

            break

    # Get files currently on disk

    filesystem_paths = set()

    for path in WATCH_DIR.rglob("*"):

        if (

            path.is_file()

            and path.suffix.lower()
            in SUPPORTED

        ):

            filesystem_paths.add(

                str(
                    path.relative_to(
                        WATCH_DIR
                    )
                )

            )

    # Delete vectors whose files disappeared

    deleted = (
        indexed_paths
        - filesystem_paths
    )

    for relative_path in deleted:

        delete_document(
            relative_path
        )


def continuous_ingestion():

    print(
        "=========================================="
    )

    print(
        " CONTINUOUS RAG INGESTION STARTED"
    )

    print(
        f" Watching: {WATCH_DIR}"
    )

    print(
        f" Scan interval: {SCAN_INTERVAL} seconds"
    )

    print(
        "=========================================="
    )

    while True:

        try:

            scan_documents()

            cleanup_deleted_documents()

        except Exception as e:

            print(
                f"[SCANNER ERROR] {e}"
            )

        time.sleep(
            SCAN_INTERVAL
        )


# ============================================================
# QUERY MODEL
# ============================================================

class Query(BaseModel):

    question: str

    top_k: int = TOP_K


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    ensure_collection()

    thread = threading.Thread(

        target=continuous_ingestion,

        daemon=True

    )

    thread.start()


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {

        "status": "ok",

        "collection": COLLECTION,

        "watch_directory": str(
            WATCH_DIR
        ),

        "scan_interval_seconds":
            SCAN_INTERVAL

    }


# ============================================================
# DOCUMENTS
# ============================================================

@app.get("/documents")
def documents():

    result = qdrant.scroll(

        collection_name=COLLECTION,

        limit=100,

        with_payload=True,

        with_vectors=False

    )

    sources = {}

    for point in result[0]:

        payload = point.payload or {}

        source = payload.get(
            "source",
            "unknown"
        )

        sources[source] = (
            sources.get(source, 0)
            + 1
        )

    return {

        "documents": sources

    }


# ============================================================
# RAG QUERY
# ============================================================

@app.post("/query")
def query(req: Query):

    if not req.question.strip():

        raise HTTPException(
            400,
            "question is required"
        )

    vector = embedder.encode(

        req.question,

        normalize_embeddings=True

    ).tolist()

    hits = qdrant.query_points(

        collection_name=COLLECTION,

        query=vector,

        limit=req.top_k,

        with_payload=True

    ).points

    results = []

    for hit in hits:

        payload = hit.payload or {}

        results.append({

            "score": hit.score,

            "source": payload.get(
                "source"
            ),

            "path": payload.get(
                "path"
            ),

            "chunk_index": payload.get(
                "chunk_index"
            ),

            "updated_at": payload.get(
                "updated_at"
            ),

            "text": payload.get(
                "text"
            )

        })

    return {

        "question": req.question,

        "results": results

    }
