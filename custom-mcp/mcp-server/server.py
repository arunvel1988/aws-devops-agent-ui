#!/usr/bin/env python3
"""
server.py

Official MCP Python SDK 1.28.1
HTTP Transport only (Streamable HTTP)

Features
--------
- investigate_server
- security_audit

Auth
----
API key auth via middleware. Set MCP_API_KEY in the environment.
Clients must send either:
  X-API-Key: <key>
or
  Authorization: Bearer <key>

Requirements
------------
pip install mcp==1.28.1
pip install psutil
pip install docker
pip install starlette

Run
---
uvicorn server:app --host 0.0.0.0 --port 8080

Docker Compose
--------------
ports:
  - "8080:8080"
environment:
  - MCP_API_KEY=${MCP_API_KEY}

IMPORTANT
---------
No mcp.run()
Only:

app = mcp.streamable_http_app()
"""

from __future__ import annotations

import json
import os
import platform
import secrets
import socket
import time
from datetime import datetime
from typing import Any, Dict, List

import docker
import psutil

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# -------------------------------------------------------------------
# API Key Auth
# -------------------------------------------------------------------

API_KEY = os.environ.get("MCP_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "MCP_API_KEY environment variable is not set. "
        "Refusing to start without an API key configured."
    )


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Simple API key auth middleware.

    Accepts either:
      X-API-Key: <key>
    or
      Authorization: Bearer <key>
    """

    async def dispatch(self, request: Request, call_next):

        supplied = request.headers.get("x-api-key")

        if not supplied:
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                supplied = auth_header[7:]

        if not supplied or not secrets.compare_digest(supplied, API_KEY):
            return JSONResponse(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid API key",
                },
                status_code=401,
            )

        return await call_next(request)


# -------------------------------------------------------------------
# MCP
# -------------------------------------------------------------------

mcp = FastMCP(
    "Infrastructure MCP Server",
    host="0.0.0.0",
    # DNS-rebinding protection defaults to localhost-only allowlists, which
    # rejects every request coming through a public hostname (e.g. the
    # Killercoda tunnel domain, an AWS-facing domain, etc). Our API key
    # middleware below is the real auth boundary, so it's safe to disable
    # the SDK's Host-header allowlist rather than hardcode a hostname that
    # may change between environments.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)

# HTTP application for Uvicorn
app = mcp.streamable_http_app()
app.add_middleware(APIKeyAuthMiddleware)

# -------------------------------------------------------------------
# Docker Client
# -------------------------------------------------------------------

try:
    docker_client = docker.from_env()
except Exception:
    docker_client = None


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def bytes_to_gb(value: int) -> float:
    return round(value / (1024 ** 3), 2)


def percent(value: float) -> float:
    return round(value, 2)


def boot_time() -> str:
    return datetime.fromtimestamp(
        psutil.boot_time()
    ).isoformat()


# -------------------------------------------------------------------
# CPU
# -------------------------------------------------------------------

def cpu_information() -> Dict[str, Any]:

    return {
        "physical_cores": psutil.cpu_count(False),
        "logical_cores": psutil.cpu_count(True),
        "usage_percent": percent(psutil.cpu_percent(interval=1)),
        "per_cpu": [
            percent(v)
            for v in psutil.cpu_percent(
                interval=1,
                percpu=True,
            )
        ],
        "load_average": (
            os.getloadavg()
            if hasattr(os, "getloadavg")
            else []
        ),
    }


# -------------------------------------------------------------------
# Memory
# -------------------------------------------------------------------

def memory_information() -> Dict[str, Any]:

    vm = psutil.virtual_memory()

    return {
        "total_gb": bytes_to_gb(vm.total),
        "used_gb": bytes_to_gb(vm.used),
        "available_gb": bytes_to_gb(vm.available),
        "free_gb": bytes_to_gb(vm.free),
        "usage_percent": percent(vm.percent),
    }


# -------------------------------------------------------------------
# Disk
# -------------------------------------------------------------------

def disk_information() -> List[Dict[str, Any]]:

    disks = []

    for part in psutil.disk_partitions(all=False):

        try:
            usage = psutil.disk_usage(part.mountpoint)

            disks.append(
                {
                    "device": part.device,
                    "mount": part.mountpoint,
                    "filesystem": part.fstype,
                    "total_gb": bytes_to_gb(usage.total),
                    "used_gb": bytes_to_gb(usage.used),
                    "free_gb": bytes_to_gb(usage.free),
                    "usage_percent": percent(
                        usage.percent
                    ),
                }
            )

        except PermissionError:
            continue

    return disks


# -------------------------------------------------------------------
# Network
# -------------------------------------------------------------------

def network_information() -> Dict[str, Any]:

    hostname = socket.gethostname()

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"

    interfaces = {}

    for interface, addrs in psutil.net_if_addrs().items():

        interfaces[interface] = []

        for addr in addrs:

            interfaces[interface].append(
                {
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                }
            )

    io = psutil.net_io_counters()

    return {
        "hostname": hostname,
        "ip_address": ip,
        "bytes_sent": io.bytes_sent,
        "bytes_received": io.bytes_recv,
        "packets_sent": io.packets_sent,
        "packets_received": io.packets_recv,
        "interfaces": interfaces,
    }


# -------------------------------------------------------------------
# Process Information
# -------------------------------------------------------------------

def top_processes(limit: int = 10) -> List[Dict[str, Any]]:

    processes = []

    for proc in psutil.process_iter(
        [
            "pid",
            "name",
            "username",
            "memory_percent",
            "cpu_percent",
            "status",
        ]
    ):

        try:

            info = proc.info

            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"],
                    "user": info["username"],
                    "cpu_percent": percent(
                        info["cpu_percent"]
                    ),
                    "memory_percent": percent(
                        info["memory_percent"]
                    ),
                    "status": info["status"],
                }
            )

        except Exception:
            pass

    processes.sort(
        key=lambda x: x["memory_percent"],
        reverse=True,
    )

    return processes[:limit]


# -------------------------------------------------------------------
# Docker Information
# -------------------------------------------------------------------

def docker_information() -> Dict[str, Any]:

    if docker_client is None:
        return {
            "available": False,
            "containers": [],
            "images": [],
            "networks": [],
            "volumes": [],
        }

    result = {
        "available": True,
        "containers": [],
        "images": [],
        "networks": [],
        "volumes": [],
    }

    # -------------------------------------------------------------
    # Containers
    # -------------------------------------------------------------

    try:

        for container in docker_client.containers.list(all=True):

            try:
                container.reload()
                attrs = container.attrs

                ports = attrs.get("NetworkSettings", {}).get("Ports", {})

                result["containers"].append(
                    {
                        "id": container.short_id,
                        "name": container.name,
                        "image": container.image.tags,
                        "status": container.status,
                        "created": attrs.get("Created"),
                        "restart_count": attrs.get("RestartCount", 0),
                        "ports": ports,
                    }
                )

            except Exception as ex:

                result["containers"].append(
                    {
                        "name": container.name,
                        "error": str(ex),
                    }
                )

    except Exception as ex:
        result["containers_error"] = str(ex)

    # -------------------------------------------------------------
    # Images
    # -------------------------------------------------------------

    try:

        for image in docker_client.images.list():

            result["images"].append(
                {
                    "id": image.short_id,
                    "tags": image.tags,
                }
            )

    except Exception as ex:
        result["images_error"] = str(ex)

    # -------------------------------------------------------------
    # Networks
    # -------------------------------------------------------------

    try:

        for network in docker_client.networks.list():

            result["networks"].append(
                {
                    "id": network.short_id,
                    "name": network.name,
                    "driver": network.attrs.get("Driver"),
                    "scope": network.attrs.get("Scope"),
                }
            )

    except Exception as ex:
        result["networks_error"] = str(ex)

    # -------------------------------------------------------------
    # Volumes
    # -------------------------------------------------------------

    try:

        volumes = docker_client.volumes.list()

        for volume in volumes:

            result["volumes"].append(
                {
                    "name": volume.name,
                    "mountpoint": volume.attrs.get(
                        "Mountpoint"
                    ),
                }
            )

    except Exception as ex:
        result["volumes_error"] = str(ex)

    return result


# -------------------------------------------------------------------
# System Information
# -------------------------------------------------------------------

def system_information() -> Dict[str, Any]:

    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": platform.architecture(),
        "boot_time": boot_time(),
        "python_version": platform.python_version(),
    }


# -------------------------------------------------------------------
# Health Score
# -------------------------------------------------------------------

def calculate_health_score(
    cpu: Dict[str, Any],
    memory: Dict[str, Any],
    disks: List[Dict[str, Any]],
) -> Dict[str, Any]:

    score = 100
    findings = []

    # CPU
    if cpu["usage_percent"] > 90:
        score -= 30
        findings.append("Critical CPU usage")

    elif cpu["usage_percent"] > 80:
        score -= 15
        findings.append("High CPU usage")

    # Memory
    if memory["usage_percent"] > 90:
        score -= 30
        findings.append("Critical memory usage")

    elif memory["usage_percent"] > 80:
        score -= 15
        findings.append("High memory usage")

    # Disk
    for disk in disks:

        if disk["usage_percent"] > 95:
            score -= 20
            findings.append(
                f"Disk nearly full ({disk['mount']})"
            )

        elif disk["usage_percent"] > 85:
            score -= 10
            findings.append(
                f"Disk usage high ({disk['mount']})"
            )

    score = max(score, 0)

    if score >= 90:
        status = "Healthy"
    elif score >= 70:
        status = "Warning"
    elif score >= 50:
        status = "Degraded"
    else:
        status = "Critical"

    return {
        "score": score,
        "status": status,
        "findings": findings,
    }


# -------------------------------------------------------------------
# MCP Tool 1
# investigate_server
# -------------------------------------------------------------------

@mcp.tool()
def investigate_server() -> Dict[str, Any]:
    """
    Collect infrastructure information from the host and Docker.
    Returns structured JSON suitable for MCP clients.
    """

    start = time.time()

    system = system_information()
    cpu = cpu_information()
    memory = memory_information()
    disks = disk_information()
    network = network_information()
    docker_info = docker_information()
    processes = top_processes()

    health = calculate_health_score(
        cpu=cpu,
        memory=memory,
        disks=disks,
    )

    elapsed_ms = round((time.time() - start) * 1000, 2)

    return {
        "success": True,
        "tool": "investigate_server",
        "timestamp": utc_now(),
        "execution_time_ms": elapsed_ms,
        "summary": {
            "health_status": health["status"],
            "health_score": health["score"],
            "hostname": system["hostname"],
        },
        "system": system,
        "cpu": cpu,
        "memory": memory,
        "disk": disks,
        "network": network,
        "docker": docker_info,
        "top_processes": processes,
        "health": health,
    }


# -------------------------------------------------------------------
# Security Checks
# -------------------------------------------------------------------

def security_checks() -> Dict[str, Any]:

    issues = []
    recommendations = []

    # -------------------------------------------------------------
    # Running as root
    # -------------------------------------------------------------

    try:

        if hasattr(os, "geteuid"):

            if os.geteuid() == 0:
                issues.append(
                    {
                        "severity": "HIGH",
                        "check": "Running as root",
                        "message": "Application is running with root privileges.",
                    }
                )

                recommendations.append(
                    "Run the container using a non-root user."
                )

    except Exception:
        pass

    # -------------------------------------------------------------
    # Docker Socket
    # -------------------------------------------------------------

    if os.path.exists("/var/run/docker.sock"):

        issues.append(
            {
                "severity": "HIGH",
                "check": "Docker socket mounted",
                "message": "/var/run/docker.sock is accessible.",
            }
        )

        recommendations.append(
            "Avoid mounting docker.sock unless absolutely required."
        )

    # -------------------------------------------------------------
    # Swap Memory
    # -------------------------------------------------------------

    swap = psutil.swap_memory()

    if swap.total == 0:

        issues.append(
            {
                "severity": "LOW",
                "check": "Swap",
                "message": "Swap memory is disabled.",
            }
        )

    # -------------------------------------------------------------
    # Disk Usage
    # -------------------------------------------------------------

    for disk in disk_information():

        if disk["usage_percent"] > 90:

            issues.append(
                {
                    "severity": "MEDIUM",
                    "check": "Disk Usage",
                    "message": (
                        f"{disk['mount']} usage "
                        f"{disk['usage_percent']}%"
                    ),
                }
            )

            recommendations.append(
                f"Clean up filesystem {disk['mount']}."
            )

    # -------------------------------------------------------------
    # Memory
    # -------------------------------------------------------------

    memory = memory_information()

    if memory["usage_percent"] > 85:

        issues.append(
            {
                "severity": "MEDIUM",
                "check": "Memory",
                "message": (
                    f"Memory usage "
                    f"{memory['usage_percent']}%"
                ),
            }
        )

        recommendations.append(
            "Investigate memory-consuming processes."
        )

    # -------------------------------------------------------------
    # CPU
    # -------------------------------------------------------------

    cpu = cpu_information()

    if cpu["usage_percent"] > 90:

        issues.append(
            {
                "severity": "HIGH",
                "check": "CPU",
                "message": (
                    f"CPU utilization "
                    f"{cpu['usage_percent']}%"
                ),
            }
        )

        recommendations.append(
            "Investigate CPU-intensive workloads."
        )

    return {
        "issues": issues,
        "recommendations": sorted(
            list(set(recommendations))
        ),
    }


# -------------------------------------------------------------------
# MCP Tool 2
# security_audit
# -------------------------------------------------------------------

@mcp.tool()
def security_audit() -> Dict[str, Any]:
    """
    Perform a lightweight security audit of the local host
    and Docker environment.
    """

    start = time.time()

    audit = security_checks()

    severity_count = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    for issue in audit["issues"]:
        severity = issue["severity"]
        severity_count[severity] += 1

    # -------------------------------------------------------------
    # Calculate overall risk
    # -------------------------------------------------------------

    if severity_count["HIGH"] > 0:
        overall_risk = "HIGH"
    elif severity_count["MEDIUM"] > 0:
        overall_risk = "MEDIUM"
    elif severity_count["LOW"] > 0:
        overall_risk = "LOW"
    else:
        overall_risk = "NONE"

    elapsed_ms = round((time.time() - start) * 1000, 2)

    return {
        "success": True,
        "tool": "security_audit",
        "timestamp": utc_now(),
        "execution_time_ms": elapsed_ms,
        "summary": {
            "overall_risk": overall_risk,
            "total_findings": len(audit["issues"]),
            "severity": severity_count,
        },
        "findings": audit["issues"],
        "recommendations": audit["recommendations"],
    }


# -------------------------------------------------------------------
# Optional Local Test
# -------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=" * 80)
    print("Testing investigate_server()")
    print("=" * 80)
    print(json.dumps(investigate_server(), indent=2))

    print()
    print("=" * 80)
    print("Testing security_audit()")
    print("=" * 80)
    print(json.dumps(security_audit(), indent=2))
