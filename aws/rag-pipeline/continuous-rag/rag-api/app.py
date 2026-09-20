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
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pypdf import PdfReader
from docx import Document

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "company_knowledge")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
WATCH_DIR = Path(os.getenv("WATCH_DIR", "/data/documents"))
TOP_K = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

app = FastAPI(title="Continuous RAG API", version="1.0.0")
qdrant = QdrantClient(url=QDRANT_URL)
embedder = SentenceTransformer(MODEL_NAME)

SUPPORTED = {".txt", ".md", ".pdf", ".docx"}

def wait_for_qdrant():
    for _ in range(60):
        try:
            qdrant.get_collections()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Qdrant did not become ready")

def ensure_collection():
    wait_for_qdrant()
    dim = embedder.get_sentence_embedding_dimension()
    names = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION not in names:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE
            )
        )

def read_document(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if path.suffix.lower() == ".docx":
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    return ""

def normalize(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def chunk_text(text: str):
    text = normalize(text)
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks

def stable_id(doc_hash: str, chunk_index: int) -> int:
    raw = hashlib.sha256(f"{doc_hash}:{chunk_index}".encode()).hexdigest()[:15]
    return int(raw, 16) % (2**63 - 1)

def delete_document(filename: str):
    qdrant.delete(
        collection_name=COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=filename)
                )]
            )
        )
    )

def ingest_file(path: Path):
    if path.suffix.lower() not in SUPPORTED or not path.exists():
        return
    try:
        text = read_document(path)
        if not text.strip():
            return

        data = path.read_bytes()
        doc_hash = hashlib.sha256(data).hexdigest()
        delete_document(path.name)

        chunks = chunk_text(text)
        vectors = embedder.encode(chunks, normalize_embeddings=True).tolist()

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(models.PointStruct(
                id=stable_id(doc_hash, i),
                vector=vector,
                payload={
                    "source": path.name,
                    "path": str(path.relative_to(WATCH_DIR)),
                    "document_hash": doc_hash,
                    "chunk_index": i,
                    "text": chunk,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            ))

        if points:
            qdrant.upsert(collection_name=COLLECTION, points=points)
            print(f"[INGESTED] {path} -> {len(points)} chunks")
    except Exception as e:
        print(f"[ERROR] {path}: {e}")

def initial_scan():
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    for path in WATCH_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            ingest_file(path)

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            time.sleep(0.5)
            ingest_file(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            time.sleep(0.5)
            ingest_file(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            ingest_file(Path(event.dest_path))

    def on_deleted(self, event):
        if not event.is_directory:
            delete_document(Path(event.src_path).name)
            print(f"[DELETED] {event.src_path}")

def start_watcher():
    initial_scan()
    observer = Observer()
    observer.schedule(Handler(), str(WATCH_DIR), recursive=True)
    observer.start()

class Query(BaseModel):
    question: str
    top_k: int = TOP_K

@app.on_event("startup")
def startup():
    ensure_collection()
    threading.Thread(target=start_watcher, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok", "collection": COLLECTION}

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
        p = point.payload or {}
        sources[p.get("source", "unknown")] = sources.get(p.get("source", "unknown"), 0) + 1
    return {"documents": sources}

@app.post("/query")
def query(req: Query):
    if not req.question.strip():
        raise HTTPException(400, "question is required")

    vector = embedder.encode(req.question, normalize_embeddings=True).tolist()
    hits = qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=req.top_k,
        with_payload=True
    ).points

    results = []
    for hit in hits:
        p = hit.payload or {}
        results.append({
            "score": hit.score,
            "source": p.get("source"),
            "path": p.get("path"),
            "chunk_index": p.get("chunk_index"),
            "updated_at": p.get("updated_at"),
            "text": p.get("text")
        })

    return {
        "question": req.question,
        "results": results
    }
