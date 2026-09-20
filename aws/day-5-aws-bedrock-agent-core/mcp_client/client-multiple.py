import logging

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient


logger = logging.getLogger(__name__)


# ============================================================
# AWS MCP SERVER
# ============================================================

AWS_MCP_SERVER_URL = "http://8.231.68.216:8080/mcp"
AWS_MCP_API_KEY = "my-super-secret-mcp-key"


# ============================================================
# RAG MCP SERVER
# ============================================================

RAG_MCP_SERVER_URL = "http://8.231.68.216:8081/mcp"
RAG_MCP_API_KEY = "my-super-secret-mcp-key"


# ============================================================
# AWS MCP CLIENT
# ============================================================

def get_aws_mcp_client() -> MCPClient:

    headers = {
        "Authorization": f"Bearer {AWS_MCP_API_KEY}"
    }

    logger.info(
        "Connecting to AWS MCP server: %s",
        AWS_MCP_SERVER_URL
    )

    return MCPClient(
        lambda: streamablehttp_client(
            AWS_MCP_SERVER_URL,
            headers=headers
        )
    )


# ============================================================
# RAG MCP CLIENT
# ============================================================

def get_rag_mcp_client() -> MCPClient:

    headers = {
        "Authorization": f"Bearer {RAG_MCP_API_KEY}"
    }

    logger.info(
        "Connecting to RAG MCP server: %s",
        RAG_MCP_SERVER_URL
    )

    return MCPClient(
        lambda: streamablehttp_client(
            RAG_MCP_SERVER_URL,
            headers=headers
        )
    )
