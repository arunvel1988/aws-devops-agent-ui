#!/usr/bin/env python3
"""
server.py

Official MCP Python SDK 1.28.1
HTTP Transport only (Streamable HTTP)

Authentication
--------------
API Key (X-API-Key)

Environment Variable
--------------------
MCP_API_KEY=my-secret-key

Run
---
uvicorn server:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import os
import json
import time
import socket
import platform

from datetime import datetime
from typing import Any, Dict, List

import docker
import psutil

from mcp.server.fastmcp import FastMCP

from starlette.responses import JSONResponse



# ----------------------------------------------------------
# API KEY
# ----------------------------------------------------------

API_KEY = os.getenv("MCP_API_KEY", "change-me")


# ----------------------------------------------------------
# MCP
# ----------------------------------------------------------

mcp = FastMCP("Infrastructure MCP Server")

# Original MCP ASGI application
mcp_app = mcp.streamable_http_app()


# ----------------------------------------------------------
# API KEY Middleware
# ----------------------------------------------------------

class ApiKeyMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode().lower(): v.decode()
            for k, v in scope["headers"]
        }

        api_key = headers.get("x-api-key")

        if api_key is None:

            auth = headers.get("authorization")

            if auth and auth.startswith("Bearer "):
                api_key = auth.replace("Bearer ", "")

        if api_key != API_KEY:

            response = JSONResponse(
                {
                    "success": False,
                    "error": "Unauthorized",
                    "message": "Invalid API Key",
                },
                status_code=401,
            )

            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# ----------------------------------------------------------
# Final ASGI Application
# ----------------------------------------------------------

app = ApiKeyMiddleware(mcp_app)


# ----------------------------------------------------------
# Docker Client
# ----------------------------------------------------------

try:
    docker_client = docker.from_env()

except Exception:
    docker_client = None


