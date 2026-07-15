from fastmcp import FastMCP
import boto3
import os
import time


mcp = FastMCP(
    "AWS DevOps SSM MCP"
)


REGION = os.getenv(
    "AWS_REGION",
    "ap-south-1"
)


ssm = boto3.client(
    "ssm",
    region_name=REGION
)



def execute_command(instance_id, command):

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


    command_id = response[
        "Command"
    ][
        "CommandId"
    ]


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



@mcp.tool()
def get_top_processes(
    instance_id: str
):

    """
    Get top CPU consuming processes
    """

    command = """

    ps aux --sort=-%cpu | head -10

    """


    return execute_command(

        instance_id,

        command

    )



@mcp.tool()
def get_memory_usage(
    instance_id: str
):

    """
    Check memory utilization
    """

    command = """

    free -m

    """


    return execute_command(

        instance_id,

        command

    )



@mcp.tool()
def kill_process(
    instance_id: str,
    pid: int
):

    """
    Kill a process using PID
    """

    command = f"""

    kill -15 {pid}

    """


    return execute_command(

        instance_id,

        command

    )



@mcp.tool()
def restart_service(
    instance_id: str,
    service_name: str
):

    """
    Restart Linux service
    """

    command = f"""

    systemctl restart {service_name}

    """


    return execute_command(

        instance_id,

        command

    )



@mcp.tool()
def disk_usage(
    instance_id: str
):

    """
    Check disk usage
    """

    command = """

    df -h

    """


    return execute_command(

        instance_id,

        command

    )



if __name__ == "__main__":


    mcp.run(

        host="0.0.0.0",

        port=8080

    )
