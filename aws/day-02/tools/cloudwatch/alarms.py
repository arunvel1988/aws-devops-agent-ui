import boto3


aws = boto3.Session(
    profile_name="user1",
    region_name="ap-south-1"
)

cloudwatch = aws.client("cloudwatch")


def get_cloudwatch_alarms(instance_id=None):

    response = cloudwatch.describe_alarms()

    alarms = response.get(
        "MetricAlarms",
        []
    )

    result = []

    for alarm in alarms:

        dimensions = alarm.get(
            "Dimensions",
            []
        )

        # If an instance_id was supplied,
        # only return alarms related to that instance.
        if instance_id:

            instance_match = False

            for dimension in dimensions:

                if (
                    dimension.get("Name")
                    == "InstanceId"
                    and
                    dimension.get("Value")
                    == instance_id
                ):
                    instance_match = True
                    break

            if not instance_match:
                continue

        result.append({

            "alarm_name":
                alarm.get("AlarmName"),

            "state":
                alarm.get("StateValue"),

            "reason":
                alarm.get("StateReason"),

            "metric":
                alarm.get("MetricName"),

            "namespace":
                alarm.get("Namespace"),

            "threshold":
                alarm.get("Threshold"),

            "comparison":
                alarm.get("ComparisonOperator")
        })

    return {
        "instance_id": instance_id,
        "alarms": result
    }
