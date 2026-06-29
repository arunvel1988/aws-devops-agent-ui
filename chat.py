import chromadb
import ollama
from sentence_transformers import SentenceTransformer

print("Connecting...")

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Connect to ChromaDB
db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_collection("company_docs")

# Connect to Ollama
client = ollama.Client(host="http://localhost:11434")

print("=" * 50)
print("AWS Company RAG Chat")
print("Type 'exit' to quit")
print("=" * 50)

while True:

    question = input("\nYou : ")

    if question.lower() == "exit":
        break

    # Create embedding for user query
    query_embedding = embedding_model.encode(question).tolist()

    # Retrieve top 3 matching chunks
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    # Combine retrieved chunks
    documents = result.get("documents", [[]])[0]

    if documents:
        context = "\n\n".join(documents)
    else:
        context = "No relevant company policy found."

    # Uncomment this for debugging
    # print("\nRetrieved Context:\n")
    # print(context)

    prompt = f"""
You are an AWS Company AI Assistant.

Rules:

1. Use the company policy below whenever it contains information relevant to the user's question.

2. If the answer is present in the company policy, answer using ONLY that information.

3. If the answer is NOT present in the company policy:
   - Answer using your general AWS, Cloud, Kubernetes, Linux, DevOps, Programming and AI knowledge.
   - Clearly mention that the information is not available in the company policy.

4. If the user greets you (hello, hi, good morning, etc.), respond normally.

5. Never invent company policies that are not present in the provided context.

==================================================
Company Policy
==================================================

{context}

==================================================
User Question
==================================================

{question}

Answer:
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

    print("\nAssistant:\n")
    print(response["message"]["content"])
