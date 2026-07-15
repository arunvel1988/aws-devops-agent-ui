#!/usr/bin/env python3

from __future__ import annotations

import os
import time
import secrets
from datetime import datetime
from typing import Dict, Any

import boto3

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# ============================================================
# MCP API KEY AUTH
# ============================================================

MCP_API_KEY = os.environ.get("MCP_API_KEY")

if not MCP_API_KEY:
    raise RuntimeError(
        "MCP_API_KEY environment variable missing"
    )


class APIKeyAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next
    ):

        supplied_key = request.headers.get(
            "x-api-key"
        )

        if not supplied_key:

            auth = request.headers.get(
                "authorization",
                ""
            )

            if auth.lower().startswith(
                "bearer "
            ):
                supplied_key = auth[7:]


        if (
            not supplied_key
            or not secrets.compare_digest(
                supplied_key,
                MCP_API_KEY
            )
        ):

            return JSONResponse(
                {
                    "error": "Unauthorized"
                },
                status_code=401
            )


        return await call_next(request)



# ============================================================
# MCP SERVER
# ============================================================


mcp = FastMCP(
    "AWS DevOps Remediation MCP",

    host="0.0.0.0",

    transport_security=
    TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)


app = mcp.streamable_http_app()

app.add_middleware(
    APIKeyAuthMiddleware
)



# ============================================================
# AWS SSM CLIENT
# ============================================================


REGION = os.getenv(
    "AWS_REGION",
    "ap-south-1"
)


ssm = boto3.client(
    "ssm",
    region_name=REGION
)



# ============================================================
# HELPERS
# ============================================================


def run_ssm_command(
    instance_id: str,
    command: str
):

    response = ssm.send_command(

        InstanceIds=[
            instance_id
        ],

        DocumentName=
        "AWS-RunShellScript",

        Parameters={
            "commands":[
                command
            ]
        }

    )


    command_id = (
        response["Command"]
        ["CommandId"]
    )


    time.sleep(3)


    result = ssm.get_command_invocation(

        CommandId=command_id,

        InstanceId=instance_id

    )


    return {

        "command_id": command_id,

        "status":
            result.get(
                "Status"
            ),

        "output":
            result.get(
                "StandardOutputContent",
                ""
            ),

        "error":
            result.get(
                "StandardErrorContent",
                ""
            )

    }



def timestamp():

    return (
        datetime.utcnow()
        .isoformat()
        + "Z"
    )



# ============================================================
# INVESTIGATION TOOLS
# ============================================================


@mcp.tool()
def get_remote_processes(
    instance_id: str
) -> Dict[str,Any]:

    """
    Find top CPU and memory consuming processes
    on EC2 instance.
    """

    command = """

    ps aux --sort=-%cpu | head -15

    """


    return {

        "timestamp":
            timestamp(),

        "instance":
            instance_id,

        "result":
            run_ssm_command(
                instance_id,
                command
            )

    }




@mcp.tool()
def check_memory(
    instance_id:str
):

    """
    Check server memory usage.
    """

    return run_ssm_command(

        instance_id,

        """
        free -m
        """

    )




@mcp.tool()
def check_disk(
    instance_id:str
):

    """
    Check disk usage.
    """

    return run_ssm_command(

        instance_id,

        """
        df -h
        """

    )



# ============================================================
# REMEDIATION TOOLS
# ============================================================


@mcp.tool()
def kill_remote_process(
    instance_id:str,
    pid:int
):

    """
    Kill high resource consuming process.
    """

    command=f"""

    kill -15 {pid}

    """


    return {

        "action":
            "kill_process",

        "pid":
            pid,

        "result":
            run_ssm_command(
                instance_id,
                command
            )

    }




@mcp.tool()
def restart_service(
    instance_id:str,
    service_name:str
):

    """
    Restart Linux service.
    """

    command=f"""

    systemctl restart {service_name}

    """


    return {

        "action":
            "restart_service",

        "service":
            service_name,

        "result":
            run_ssm_command(
                instance_id,
                command
            )

    }




@mcp.tool()
def clear_temp_files(
    instance_id:str
):

    """
    Cleanup temporary files.
    """

    command="""

    rm -rf /tmp/*

    """


    return run_ssm_command(

        instance_id,

        command

    )



@mcp.tool()
def restart_application(
    instance_id:str,
    service_name:str
):

    """
    Application remediation action.
    """

    return restart_service(
        instance_id,
        service_name
    )



# ============================================================
# HEALTH
# ============================================================


@mcp.tool()
def health_check():

    return {

        "status":"healthy",

        "service":
            "AWS DevOps Remediation MCP",

        "region":
            REGION,

        "time":
            timestamp()

    }



# ============================================================
# START
# ============================================================


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        app,

        host="0.0.0.0",

        port=8080

    )
