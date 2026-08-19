import boto3
from datetime import datetime, timedelta, timezone


# ==========================================================
# AWS SESSION
# ==========================================================

aws = boto3.Session(
    profile_name="user1",
    region_name="ap-south-1"
)

cloudwatch = aws.client("cloudwatch")


# ==========================================================
# CPU UTILIZATION
# ==========================================================

def get_cpu_utilization(instance_id):

    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(minutes=30)

    response = cloudwatch.get_metric_statistics(

        Namespace="AWS/EC2",

        MetricName="CPUUtilization",

        Dimensions=[
            {
                "Name": "InstanceId",
                "Value": instance_id
            }
        ],

        StartTime=start_time,

        EndTime=end_time,

        Period=300,

        Statistics=[
            "Average",
            "Maximum"
        ]
    )

    datapoints = response.get(
        "Datapoints",
        []
    )

    datapoints.sort(
        key=lambda x: x["Timestamp"]
    )

    result = []

    for point in datapoints:

        result.append({

            "timestamp":
                point["Timestamp"].isoformat(),

            "average":
                point.get("Average"),

            "maximum":
                point.get("Maximum")
        })

    # Return the latest datapoint
    if result:

        latest = result[-1]

        return {
            "instance_id": instance_id,
            "timestamp": latest["timestamp"],
            "average_cpu": latest["average"],
            "maximum_cpu": latest["maximum"]
        }

    return {
        "instance_id": instance_id,
        "timestamp": None,
        "average_cpu": None,
        "maximum_cpu": None
    }


# ==========================================================
# NETWORK METRICS
# ==========================================================

def get_network_metrics(instance_id):

    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(minutes=30)

    metrics = [
        "NetworkIn",
        "NetworkOut"
    ]

    result = {}

    for metric_name in metrics:

        response = cloudwatch.get_metric_statistics(

            Namespace="AWS/EC2",

            MetricName=metric_name,

            Dimensions=[
                {
                    "Name": "InstanceId",
                    "Value": instance_id
                }
            ],

            StartTime=start_time,

            EndTime=end_time,

            Period=300,

            Statistics=[
                "Average",
                "Maximum"
            ]
        )

        datapoints = response.get(
            "Datapoints",
            []
        )

        datapoints.sort(
            key=lambda x: x["Timestamp"]
        )

        metric_result = []

        for point in datapoints:

            metric_result.append({

                "timestamp":
                    point["Timestamp"].isoformat(),

                "average":
                    point.get("Average"),

                "maximum":
                    point.get("Maximum")
            })

        result[metric_name] = metric_result

    return {
        "instance_id": instance_id,
        "metrics": result
    }


# ==========================================================
# DISK METRICS
# ==========================================================

def get_disk_metrics(instance_id):

    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(minutes=30)

    metrics = [
        "DiskReadBytes",
        "DiskWriteBytes"
    ]

    result = {}

    for metric_name in metrics:

        response = cloudwatch.get_metric_statistics(

            Namespace="AWS/EC2",

            MetricName=metric_name,

            Dimensions=[
                {
                    "Name": "InstanceId",
                    "Value": instance_id
                }
            ],

            StartTime=start_time,

            EndTime=end_time,

            Period=300,

            Statistics=[
                "Average",
                "Maximum"
            ]
        )

        datapoints = response.get(
            "Datapoints",
            []
        )

        datapoints.sort(
            key=lambda x: x["Timestamp"]
        )

        metric_result = []

        for point in datapoints:

            metric_result.append({

                "timestamp":
                    point["Timestamp"].isoformat(),

                "average":
                    point.get("Average"),

                "maximum":
                    point.get("Maximum")
            })

        result[metric_name] = metric_result

    return {
        "instance_id": instance_id,
        "metrics": result
    }
