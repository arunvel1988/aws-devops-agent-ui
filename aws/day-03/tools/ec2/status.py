import boto3


aws = boto3.Session(
    profile_name="user1",
    region_name="ap-south-1"
)

ec2 = aws.client("ec2")


def get_instance_status(instance_id):

    response = ec2.describe_instance_status(
        InstanceIds=[instance_id],
        IncludeAllInstances=True
    )

    statuses = response.get(
        "InstanceStatuses",
        []
    )

    if not statuses:
        return {
            "instance_id": instance_id,
            "state": "unknown",
            "system_status": "unknown",
            "instance_status": "unknown"
        }

    status = statuses[0]

    return {
        "instance_id": instance_id,

        "state": status.get(
            "InstanceState", {}
        ).get("Name"),

        "system_status": status.get(
            "SystemStatus", {}
        ).get("Status"),

        "instance_status": status.get(
            "InstanceStatus", {}
        ).get("Status")
    }

