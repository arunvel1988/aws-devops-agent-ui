from tools.ec2.instances import get_ec2_instances
from tools.ec2.status import get_instance_status

from tools.cloudwatch.metrics import (
    get_cpu_utilization,
    get_network_metrics,
    get_disk_metrics
)

from tools.cloudwatch.alarms import get_cloudwatch_alarms

from tools.ssm.processes import get_top_processes


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
        get_top_processes
}


# ==========================================================
# TOOL DEFINITIONS
# ==========================================================

TOOL_DEFINITIONS = [

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

    {
        "type": "function",
        "name": "get_instance_status",
        "description":
            "Get EC2 instance state and system and instance status checks.",
        "parameters": {
            "type": "object",
            "properties": {
                "instance_id": {
                    "type": "string",
                    "description": "The EC2 instance ID."
                }
            },
            "required": ["instance_id"]
        }
    },

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
                    "description": "The EC2 instance ID."
                }
            },
            "required": ["instance_id"]
        }
    },

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
                    "description": "The EC2 instance ID."
                }
            },
            "required": ["instance_id"]
        }
    },

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
                    "description": "The EC2 instance ID."
                }
            },
            "required": ["instance_id"]
        }
    },

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
                    "description": "The EC2 instance ID."
                }
            },
            "required": ["instance_id"]
        }
    },

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
                    "description": "The EC2 instance ID."
                }
            },
            "required": ["instance_id"]
        }
    }
]
