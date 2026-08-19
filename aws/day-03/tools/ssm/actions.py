import boto3
import time


aws = boto3.Session(
    profile_name="user1",
    region_name="ap-south-1"
)

ssm = aws.client("ssm")


def kill_process(instance_id, pid):
    """
    Terminate a specific process on an EC2 instance.

    This function should ONLY be called after
    explicit human approval.
    """

    command = f"kill -TERM {int(pid)}"

    response = ssm.send_command(
        InstanceIds=[instance_id],

        DocumentName="AWS-RunShellScript",

        Parameters={
            "commands": [command]
        }
    )

    command_id = response["Command"]["CommandId"]

    time.sleep(2)

    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    return {
        "instance_id": instance_id,
        "pid": pid,
        "command_id": command_id,
        "status": result.get("Status"),
        "stdout": result.get("StandardOutputContent"),
        "stderr": result.get("StandardErrorContent")
    }
