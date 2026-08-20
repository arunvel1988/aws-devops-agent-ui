cat registry.py 
from tools.ec2.instances import get_ec2_instances
from tools.ec2.status import get_instance_status

from tools.cloudwatch.metrics import (
    get_cpu_utilization,
    get_network_metrics,
    get_disk_metrics
)

from tools.cloudwatch.alarms import get_cloudwatch_alarms

from tools.ssm.processes import get_top_processes
from tools.ssm.terminate import terminate_process


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
        get_disk_metrics,

    "get_top_processes":
        get_top_processes,

    "terminate_process":
        terminate_process
}


# ==========================================================
# TOOL DEFINITIONS
# ==========================================================

TOOL_DEFINITIONS = [

    # ------------------------------------------------------
    # EC2 INSTANCES
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_ec2_instances",

        "description":
            "Get information about EC2 instances in the AWS account.",

        "parameters": {
            "type": "object",

            "properties": {},

            "required": []
        }
    },

    # ------------------------------------------------------
    # INSTANCE STATUS
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_instance_status",

        "description":
            "Get the EC2 instance state and AWS system and instance status checks.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

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
    # CPU
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_cpu_utilization",

        "description":
            "Get CPU utilization metrics for an EC2 instance.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

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
    # CLOUDWATCH ALARMS
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_cloudwatch_alarms",

        "description":
            "Get CloudWatch alarms related to an EC2 instance.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

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
    # NETWORK
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_network_metrics",

        "description":
            "Get network traffic metrics for an EC2 instance.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

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
    # DISK
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_disk_metrics",

        "description":
            "Get disk I/O metrics for an EC2 instance.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

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
    # TOP PROCESSES
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "get_top_processes",

        "description":
            "Get the top CPU-consuming processes running on an EC2 instance using AWS Systems Manager. This tool only investigates processes and does not terminate anything.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

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
    # TERMINATE PROCESS
    # ------------------------------------------------------

    {
        "type": "function",

        "name": "terminate_process",

        "description":
            "Terminate a specific process on an EC2 instance using AWS Systems Manager. This is a destructive action. It must only be executed after explicit human approval.",

        "parameters": {
            "type": "object",

            "properties": {

                "instance_id": {
                    "type": "string",

                    "description":
                        "The EC2 instance ID."
                },

                "pid": {
                    "type": "integer",

                    "description":
                        "The process ID to terminate."
                }
            },

            "required": [
                "instance_id",
                "pid"
            ]
        }
    }
]
