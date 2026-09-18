import logging

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient


logger = logging.getLogger(__name__)


# ============================================================
# MCP SERVER CONFIGURATION
# ============================================================

MCP_SERVER_URL = "https://013396ae0c2c6fa8-1-8080.papa.r.killercoda.com/mcp"

MCP_API_KEY = "my-super-secret-mcp-key"


# ============================================================
# MCP CLIENT
# ============================================================

def get_streamable_http_mcp_client() -> MCPClient:
    """
    Connect to the remote MCP server using
    Streamable HTTP and Bearer token authentication.
    """

    headers = {
        "Authorization": f"Bearer {MCP_API_KEY}"
    }

    logger.info(
        "Connecting to MCP server: %s",
        MCP_SERVER_URL
    )

    return MCPClient(
        lambda: streamablehttp_client(
            MCP_SERVER_URL,
            headers=headers
        )
    )
