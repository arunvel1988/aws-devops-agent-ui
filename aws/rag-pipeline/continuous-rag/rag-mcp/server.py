import os
import httpx
from fastmcp import FastMCP

RAG_API_URL = os.getenv("RAG_API_URL", "http://rag-api:8000")

mcp = FastMCP("company-rag")

@mcp.tool()
async def search_company_knowledge(question: str, top_k: int = 5) -> str:
    """Search the continuously updated company knowledge base for relevant policies, runbooks, incidents, architecture and operational documents."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{RAG_API_URL}/query",
            json={"question": question, "top_k": top_k}
        )
        response.raise_for_status()
        data = response.json()

    if not data["results"]:
        return "No relevant company knowledge was found."

    lines = []
    for i, item in enumerate(data["results"], 1):
        lines.append(
            f"[Result {i}] source={item['source']} "
            f"path={item['path']} score={item['score']:.4f} "
            f"updated_at={item['updated_at']}\n{item['text']}"
        )
    return "\n\n".join(lines)

@mcp.tool()
async def list_company_documents() -> str:
    """List documents currently indexed by the company knowledge RAG pipeline."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{RAG_API_URL}/documents")
        response.raise_for_status()
        data = response.json()

    if not data["documents"]:
        return "No documents are currently indexed."

    return "\n".join(
        f"{name}: {count} chunks"
        for name, count in data["documents"].items()
    )

if __name__ == "__main__":
    # Streamable HTTP MCP endpoint on port 8080.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
