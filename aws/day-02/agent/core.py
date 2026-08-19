from openai import OpenAI
import json

from agent.registry import TOOL_DEFINITIONS
from agent.executor import execute_tool

from memory.store import (
    get_response_id,
    save_response_id
)


client = OpenAI()


# ==========================================================
# RUN AGENT
# ==========================================================

def run_agent(user_message, session_id="default"):

    print()
    print("=" * 40)
    print("AWS DEVOPS AGENT")
    print("=" * 40)

    print(f"Session ID: {session_id}")

    previous_response_id = get_response_id(session_id)

    print(
        f"Previous response ID: "
        f"{previous_response_id}"
    )

    # ======================================================
    # SPECIAL INVESTIGATION
    # ======================================================

    investigation_words = [
        "investigate my ec2",
        "investigate my instance",
        "check my ec2",
        "check my instance",
        "health check my ec2",
        "check ec2 health"
    ]

    is_investigation = any(
        word in user_message.lower()
        for word in investigation_words
    )

    # ======================================================
    # NORMAL AGENT
    # ======================================================

    if not is_investigation:

        return run_normal_agent(
            user_message,
            session_id,
            previous_response_id
        )

    # ======================================================
    # INVESTIGATION WORKFLOW
    # ======================================================

    print()
    print("=" * 40)
    print("STARTING EC2 INVESTIGATION")
    print("=" * 40)

    # ------------------------------------------------------
    # 1. Get EC2 instances
    # ------------------------------------------------------

    print()
    print("1. Checking EC2 instances...")

    instances = execute_tool(
        "get_ec2_instances",
        {}
    )

    print("EC2 RESULT:")
    print(instances)

    # ------------------------------------------------------
    # Find running instance
    # ------------------------------------------------------

    running_instances = [
        instance
        for instance in instances
        if instance.get("state") == "running"
    ]

    if not running_instances:

        return "No running EC2 instance was found."

    instance = running_instances[0]

    instance_id = instance["instance_id"]

    print()
    print(
        f"Running instance found: "
        f"{instance_id}"
    )

    # ------------------------------------------------------
    # 2. CPU
    # ------------------------------------------------------

    print()
    print("2. Checking CPU...")

    cpu = execute_tool(
        "get_cpu_utilization",
        {
            "instance_id": instance_id
        }
    )

    print("CPU RESULT:")
    print(cpu)

    # ------------------------------------------------------
    # 3. Instance status
    # ------------------------------------------------------

    print()
    print("3. Checking instance status...")

    status = execute_tool(
        "get_instance_status",
        {
            "instance_id": instance_id
        }
    )

    print("STATUS RESULT:")
    print(status)

    # ------------------------------------------------------
    # 4. CloudWatch alarms
    # ------------------------------------------------------

    print()
    print("4. Checking CloudWatch alarms...")

    alarms = execute_tool(
        "get_cloudwatch_alarms",
        {
            "instance_id": instance_id
        }
    )

    print("ALARM RESULT:")
    print(alarms)

    # ------------------------------------------------------
    # 5. Network
    # ------------------------------------------------------

    print()
    print("5. Checking network metrics...")

    network = execute_tool(
        "get_network_metrics",
        {
            "instance_id": instance_id
        }
    )

    print("NETWORK RESULT:")
    print(network)

    # ------------------------------------------------------
    # 6. Disk
    # ------------------------------------------------------

    print()
    print("6. Checking disk metrics...")

    disk = execute_tool(
        "get_disk_metrics",
        {
            "instance_id": instance_id
        }
    )

    print("DISK RESULT:")
    print(disk)

    # ======================================================
    # SEND ALL DATA TO GPT-OSS FOR ANALYSIS
    # ======================================================

    investigation_data = {

        "instance": instance,

        "cpu": cpu,

        "instance_status": status,

        "cloudwatch_alarms": alarms,

        "network": network,

        "disk": disk
    }

    prompt = f"""
You are an AWS DevOps Agent.

Perform a health investigation of the EC2 instance.

Do not invent information.

Use ONLY the AWS data provided below.

Determine:

1. Whether the instance is healthy.
2. Whether CPU is abnormal.
3. Whether system or instance status checks are abnormal.
4. Whether CloudWatch alarms indicate a problem.
5. Whether network metrics show anything unusual.
6. Whether disk metrics show anything unusual.
7. Give an overall NORMAL or ABNORMAL verdict.
8. Explain the reason clearly.

AWS INVESTIGATION DATA:

{json.dumps(investigation_data, indent=2)}

Give a concise DevOps investigation report.
"""

    print()
    print("=" * 40)
    print("SENDING INVESTIGATION TO GPT-OSS")
    print("=" * 40)

    # ======================================================
    # GPT-OSS ANALYSIS
    # ======================================================

    response = client.responses.create(

        model="openai.gpt-oss-120b",

        input=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # ------------------------------------------------------
    # Save response for session memory
    # ------------------------------------------------------

    save_response_id(
        session_id,
        response.id
    )

    print()
    print("=" * 40)
    print("INVESTIGATION COMPLETE")
    print("=" * 40)

    print(
        f"Response ID: {response.id}"
    )

    return response.output_text


# ==========================================================
# NORMAL AGENT
# ==========================================================

def run_normal_agent(
    user_message,
    session_id,
    previous_response_id
):

    # ------------------------------------------------------
    # First request
    # ------------------------------------------------------

    if previous_response_id:

        response = client.responses.create(

            model="openai.gpt-oss-120b",

            previous_response_id=
                previous_response_id,

            input=[
                {
                    "role": "user",
                    "content": user_message
                }
            ],

            tools=TOOL_DEFINITIONS
        )

    else:

        response = client.responses.create(

            model="openai.gpt-oss-120b",

            input=[
                {
                    "role": "user",
                    "content": user_message
                }
            ],

            tools=TOOL_DEFINITIONS
        )

    # ======================================================
    # TOOL LOOP
    # ======================================================

    while True:

        tool_outputs = []

        for item in response.output:

            if item.type == "function_call":

                print()
                print(
                    f"Agent requested tool: "
                    f"{item.name}"
                )

                arguments = json.loads(
                    item.arguments or "{}"
                )

                print(
                    f"Tool arguments: "
                    f"{arguments}"
                )

                result = execute_tool(
                    item.name,
                    arguments
                )

                print("AWS tool result:")
                print(result)

                tool_outputs.append({

                    "type":
                        "function_call_output",

                    "call_id":
                        item.call_id,

                    "output":
                        json.dumps(result)
                })

        # --------------------------------------------------
        # Agent finished
        # --------------------------------------------------

        if not tool_outputs:

            save_response_id(
                session_id,
                response.id
            )

            print()
            print("=" * 40)
            print("AGENT FINISHED")
            print("=" * 40)

            print(
                f"Response ID: "
                f"{response.id}"
            )

            return response.output_text

        # --------------------------------------------------
        # Send tool results back
        # --------------------------------------------------

        response = client.responses.create(

            model="openai.gpt-oss-120b",

            previous_response_id=
                response.id,

            input=tool_outputs,

            tools=TOOL_DEFINITIONS
        )
