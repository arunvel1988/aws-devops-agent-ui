import os
import re
import glob
import chromadb
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection("company_docs")

# -------------------------------------------------------
# Delete old embeddings
# -------------------------------------------------------
print("Deleting old embeddings...")

try:
    existing = collection.get()

    if existing["ids"]:
        collection.delete(ids=existing["ids"])

except Exception:
    pass

# -------------------------------------------------------
# Read all TXT files
# -------------------------------------------------------
documents = []

txt_files = glob.glob("*.txt")

if not txt_files:
    print("No .txt files found!")
    exit()

print("\nReading text files...\n")

for filename in sorted(txt_files):

    print(f"Reading {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    # -------------------------------------------------------
    # Split using ===== if present
    # -------------------------------------------------------

    if "==========" in text:

        parts = re.split(r"={5,}", text)

        for part in parts:

            part = part.strip()

            if len(part) < 20:
                continue

            documents.append(
                {
                    "source": filename,
                    "text": part
                }
            )

    else:

        # ---------------------------------------------------
        # Split into ~500 character chunks
        # ---------------------------------------------------

        lines = text.splitlines()

        chunk = ""

        for line in lines:

            if len(chunk) + len(line) < 500:
                chunk += line + "\n"

            else:
                documents.append(
                    {
                        "source": filename,
                        "text": chunk.strip()
                    }
                )

                chunk = line + "\n"

        if chunk.strip():

            documents.append(
                {
                    "source": filename,
                    "text": chunk.strip()
                }
            )

print("\n========================================")
print("Chunks Created")
print("========================================")

for i, doc in enumerate(documents):

    print(f"\nChunk {i+1}")
    print(f"Source : {doc['source']}")
    print("-" * 60)
    print(doc["text"])
    print()

# -------------------------------------------------------
# Generate Embeddings
# -------------------------------------------------------

print("\nGenerating embeddings...")

texts = [doc["text"] for doc in documents]

embeddings = model.encode(texts).tolist()

ids = [f"chunk_{i}" for i in range(len(documents))]

metadatas = []

for i, doc in enumerate(documents):

    metadatas.append(
        {
            "chunk": i + 1,
            "source": doc["source"]
        }
    )

collection.add(
    ids=ids,
    documents=texts,
    embeddings=embeddings,
    metadatas=metadatas
)

print("\n========================================")
print("Embedding Complete")
print(f"Files Processed : {len(txt_files)}")
print(f"Total Chunks    : {collection.count()}")
print("========================================")

print("\nFiles Embedded:")

for file in sorted(txt_files):
    print(f" - {file}")

print("\nDone.")
