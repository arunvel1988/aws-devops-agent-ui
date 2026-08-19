import boto3
import time


aws = boto3.Session(
    profile_name="user1",
    region_name="ap-south-1"
)

ssm = aws.client("ssm")


def get_top_processes(instance_id):

    command = """
ps -eo pid,ppid,user,%cpu,%mem,etime,comm,args --sort=-%cpu | head -n 11
"""

    response = ssm.send_command(
        InstanceIds=[instance_id],

        DocumentName="AWS-RunShellScript",

        Parameters={
            "commands": [command]
        }
    )

    command_id = response["Command"]["CommandId"]

    # Wait briefly for SSM to execute the command
    time.sleep(3)

    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    return {
        "instance_id": instance_id,
        "status": result.get("Status"),
        "stdout": result.get("StandardOutputContent"),
        "stderr": result.get("StandardErrorContent")
    }


