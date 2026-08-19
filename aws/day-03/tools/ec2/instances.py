import boto3


aws = boto3.Session(
    profile_name="user1",
    region_name="ap-south-1"
)

ec2 = aws.client("ec2")


def get_ec2_instances():
    response = ec2.describe_instances()

    instances = []

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instances.append({
                "instance_id": instance["InstanceId"],
                "state": instance["State"]["Name"],
                "instance_type": instance["InstanceType"],
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress")
            })

    return instances
