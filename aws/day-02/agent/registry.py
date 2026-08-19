from tools.ec2.instances import get_ec2_instances
from tools.ec2.status import get_instance_status

from tools.cloudwatch.metrics import (
    get_cpu_utilization,
    get_network_metrics,
    get_disk_metrics
)

from tools.cloudwatch.alarms import (
    get_cloudwatch_alarms
)


# ==========================================================
# TOOL FUNCTIONS
# ==========================================================

TOOL_FUNCTIONS = {

    "get_ec2_instances":
        get_ec2_instances,

    "get_instance_status":
        get_instance_status,

    "get_cpu_utilization":
        get_cpu_utilization,

    "get_cloudwatch_alarms":
        get_cloudwatch_alarms,

    "get_network_metrics":
        get_network_metrics,

    "get_disk_metrics":
        get_disk_metrics
}


# ==========================================================
# TOOL DEFINITIONS
# ==========================================================

TOOL_DEFINITIONS = [

    # ------------------------------------------------------
    # 1. EC2 INSTANCES
    # ------------------------------------------------------

    {
        "type": "function",

        "name":
            "get_ec2_instances",

        "description":
            "Get information about EC2 instances in the AWS account.",

        "parameters": {

            "type":
                "object",

            "properties":
                {},

            "required":
                []
        }
    },


    # ------------------------------------------------------
    # 2. INSTANCE STATUS
    # ------------------------------------------------------

    {
        "type": "function",

        "name":
            "get_instance_status",

        "description":
            "Get the EC2 instance state, system status check, and instance status check.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "instance_id": {

                    "type":
                        "string",

                    "description":
                        "The EC2 instance ID, for example i-1234567890abcdef0."
                }
            },

            "required": [
                "instance_id"
            ]
        }
    },


    # ------------------------------------------------------
    # 3. CPU
    # ------------------------------------------------------

    {
        "type":
            "function",

        "name":
            "get_cpu_utilization",

        "description":
            "Get the latest CPU utilization for an EC2 instance using CloudWatch.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "instance_id": {

                    "type":
                        "string",

                    "description":
                        "The EC2 instance ID."
                }
            },

            "required": [
                "instance_id"
            ]
        }
    },


    # ------------------------------------------------------
    # 4. CLOUDWATCH ALARMS
    # ------------------------------------------------------

    {
        "type":
            "function",

        "name":
            "get_cloudwatch_alarms",

        "description":
            "Get CloudWatch alarms associated with an EC2 instance and their current state.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "instance_id": {

                    "type":
                        "string",

                    "description":
                        "The EC2 instance ID used to filter alarms."
                }
            },

            "required": [
                "instance_id"
            ]
        }
    },


    # ------------------------------------------------------
    # 5. NETWORK
    # ------------------------------------------------------

    {
        "type":
            "function",

        "name":
            "get_network_metrics",

        "description":
            "Get NetworkIn and NetworkOut CloudWatch metrics for an EC2 instance for the last 30 minutes.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "instance_id": {

                    "type":
                        "string",

                    "description":
                        "The EC2 instance ID."
                }
            },

            "required": [
                "instance_id"
            ]
        }
    },


    # ------------------------------------------------------
    # 6. DISK
    # ------------------------------------------------------

    {
        "type":
            "function",

        "name":
            "get_disk_metrics",

        "description":
            "Get disk read and write CloudWatch metrics for an EC2 instance for the last 30 minutes.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "instance_id": {

                    "type":
                        "string",

                    "description":
                        "The EC2 instance ID."
                }
            },

            "required": [
                "instance_id"
            ]
        }
    }
]
