import chromadb
import ollama
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

print("Connecting ChromaDB...")
db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_collection("company_docs")

print("Connecting Ollama...")
client = ollama.Client(host="http://localhost:11434")


def ask(question):

    question = question.strip()

    # ---------------------------------------
    # Search ChromaDB
    # ---------------------------------------

    query_embedding = embedding_model.encode(question).tolist()

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["documents", "metadatas"]
    )

    documents = result["documents"][0]
    metadatas = result["metadatas"][0]

    context = ""

    print("\nRetrieved Documents")
    print("=" * 70)

    for doc, meta in zip(documents, metadatas):

        print(f"Source : {meta['source']}")
        print("-" * 70)
        print(doc)
        print()

        context += f"""
Source: {meta['source']}
{doc}

"""

    prompt = f"""
You are a helpful AI assistant.

You have access to company documents.

Instructions:

1. Read the Context carefully.

2. If the Context clearly contains the answer to the user's question,
   answer ONLY using the Context.

3. If the Context is unrelated to the user's question,
   IGNORE the Context completely.

4. In that case, answer normally using your own knowledge.

5. Never say:
   - "The documents do not contain..."
   - "Based on the context..."
   - "According to the retrieved documents..."

Simply answer naturally.

========================
Context
========================

{context}

========================
Question
========================

{question}
"""

    response = client.chat(
        model="qwen2.5:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]
