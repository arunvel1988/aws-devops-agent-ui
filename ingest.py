import chromadb
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection("company_docs")

# Delete old data
try:
    collection.delete(ids=collection.get()["ids"])
except:
    pass

print("Reading document...")

with open("company_policy.txt", "r", encoding="utf-8") as f:
    text = f.read()

# -------- Chunking --------
chunk_size = 500
overlap = 100

chunks = []

start = 0

while start < len(text):
    end = start + chunk_size
    chunks.append(text[start:end])
    start += chunk_size - overlap

print(f"Total Chunks : {len(chunks)}")

embeddings = model.encode(chunks).tolist()

ids = [f"chunk_{i}" for i in range(len(chunks))]

collection.add(
    ids=ids,
    documents=chunks,
    embeddings=embeddings
)

print("=" * 50)
print("Embedding Complete")
print("Chunks Stored :", collection.count())
print("=" * 50)
