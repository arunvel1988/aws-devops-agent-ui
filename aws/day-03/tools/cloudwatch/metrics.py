<pre>import boto3
from datetime import datetime, timedelta, timezone


# ==========================================================
# AWS SESSION
# ==========================================================

aws = boto3.Session(
    profile_name=&quot;user1&quot;,
    region_name=&quot;ap-south-1&quot;
)

cloudwatch = aws.client(&quot;cloudwatch&quot;)


# ==========================================================
# CPU UTILIZATION
# ==========================================================

def get_cpu_utilization(instance_id):

    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(minutes=30)

    response = cloudwatch.get_metric_statistics(

        Namespace=&quot;AWS/EC2&quot;,

        MetricName=&quot;CPUUtilization&quot;,

        Dimensions=[
            {
                &quot;Name&quot;: &quot;InstanceId&quot;,
                &quot;Value&quot;: instance_id
            }
        ],

        StartTime=start_time,

        EndTime=end_time,

        Period=300,

        Statistics=[
            &quot;Average&quot;,
            &quot;Maximum&quot;
        ]
    )

    datapoints = response.get(
        &quot;Datapoints&quot;,
        []
    )

    datapoints.sort(
        key=lambda x: x[&quot;Timestamp&quot;]
    )

    result = []

    for point in datapoints:

        result.append({

            &quot;timestamp&quot;:
                point[&quot;Timestamp&quot;].isoformat(),

            &quot;average&quot;:
                point.get(&quot;Average&quot;),

            &quot;maximum&quot;:
                point.get(&quot;Maximum&quot;)
        })

    # Return the latest datapoint
    if result:

        latest = result[-1]

        return {
            &quot;instance_id&quot;: instance_id,
            &quot;timestamp&quot;: latest[&quot;timestamp&quot;],
            &quot;average_cpu&quot;: latest[&quot;average&quot;],
            &quot;maximum_cpu&quot;: latest[&quot;maximum&quot;]
        }

    return {
        &quot;instance_id&quot;: instance_id,
        &quot;timestamp&quot;: None,
        &quot;average_cpu&quot;: None,
        &quot;maximum_cpu&quot;: None
    }


# ==========================================================
# NETWORK METRICS
# ==========================================================

def get_network_metrics(instance_id):

    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(minutes=30)

    metrics = [
        &quot;NetworkIn&quot;,
        &quot;NetworkOut&quot;
    ]

    result = {}

    for metric_name in metrics:

        response = cloudwatch.get_metric_statistics(

            Namespace=&quot;AWS/EC2&quot;,

            MetricName=metric_name,

            Dimensions=[
                {
                    &quot;Name&quot;: &quot;InstanceId&quot;,
                    &quot;Value&quot;: instance_id
                }
            ],

            StartTime=start_time,

            EndTime=end_time,

            Period=300,

            Statistics=[
                &quot;Average&quot;,
                &quot;Maximum&quot;
            ]
        )

        datapoints = response.get(
            &quot;Datapoints&quot;,
            []
        )

        datapoints.sort(
            key=lambda x: x[&quot;Timestamp&quot;]
        )

        metric_result = []

        for point in datapoints:

            metric_result.append({

                &quot;timestamp&quot;:
                    point[&quot;Timestamp&quot;].isoformat(),

                &quot;average&quot;:
                    point.get(&quot;Average&quot;),

                &quot;maximum&quot;:
                    point.get(&quot;Maximum&quot;)
            })

        result[metric_name] = metric_result

    return {
        &quot;instance_id&quot;: instance_id,
        &quot;metrics&quot;: result
    }


# ==========================================================
# DISK METRICS
# ==========================================================

def get_disk_metrics(instance_id):

    end_time = datetime.now(timezone.utc)

    start_time = end_time - timedelta(minutes=30)

    metrics = [
        &quot;DiskReadBytes&quot;,
        &quot;DiskWriteBytes&quot;
    ]

    result = {}

    for metric_name in metrics:

        response = cloudwatch.get_metric_statistics(

            Namespace=&quot;AWS/EC2&quot;,

            MetricName=metric_name,

            Dimensions=[
                {
                    &quot;Name&quot;: &quot;InstanceId&quot;,
                    &quot;Value&quot;: instance_id
                }
            ],

            StartTime=start_time,

            EndTime=end_time,

            Period=300,

            Statistics=[
                &quot;Average&quot;,
                &quot;Maximum&quot;
            ]
        )

        datapoints = response.get(
            &quot;Datapoints&quot;,
            []
        )

        datapoints.sort(
            key=lambda x: x[&quot;Timestamp&quot;]
        )

        metric_result = []

        for point in datapoints:

            metric_result.append({

                &quot;timestamp&quot;:
                    point[&quot;Timestamp&quot;].isoformat(),

                &quot;average&quot;:
                    point.get(&quot;Average&quot;),

                &quot;maximum&quot;:
                    point.get(&quot;Maximum&quot;)
            })

        result[metric_name] = metric_result

    return {
        &quot;instance_id&quot;: instance_id,
        &quot;metrics&quot;: result
    }
</pre>
