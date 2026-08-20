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
# HUMAN APPROVAL STATE
# ==========================================================

PENDING_APPROVALS = {}


# ==========================================================
# RUN AGENT
# ==========================================================

def run_agent(user_message, session_id="default"):

    print()
    print("=" * 40)
    print("AWS DEVOPS AGENT")
    print("=" * 40)

    print(f"Session ID: {session_id}")

    previous_response_id = get_response_id(
        session_id
    )

    print(
        f"Previous response ID: "
        f"{previous_response_id}"
    )

    message_lower = user_message.lower().strip()


    # ======================================================
    # HUMAN APPROVAL
    # ======================================================

    approval_words = [
        "yes",
        "yes please",
        "approve",
        "approved",
        "proceed",
        "terminate",
        "kill it",
        "kill"
    ]

    rejection_words = [
        "no",
        "nope",
        "reject",
        "rejected",
        "cancel",
        "don't",
        "do not",
        "stop"
    ]


    # ------------------------------------------------------
    # Check pending approval
    # ------------------------------------------------------

    if session_id in PENDING_APPROVALS:

        pending = PENDING_APPROVALS[session_id]


        # --------------------------------------------------
        # APPROVED
        # --------------------------------------------------

        if message_lower in approval_words:

            print()
            print("=" * 40)
            print("HUMAN APPROVAL RECEIVED")
            print("=" * 40)

            instance_id = pending["instance_id"]
            pid = pending["pid"]

            print(
                f"Approved termination of PID {pid}"
            )

            del PENDING_APPROVALS[session_id]

            print()
            print("Executing terminate_process...")

            result = execute_tool(
                "terminate_process",
                {
                    "instance_id": instance_id,
                    "pid": pid
                }
            )

            print("TERMINATION RESULT:")
            print(result)

            return format_termination_result(
                pending,
                result
            )


        # --------------------------------------------------
        # REJECTED
        # --------------------------------------------------

        if message_lower in rejection_words:

            print()
            print("=" * 40)
            print("HUMAN APPROVAL REJECTED")
            print("=" * 40)

            del PENDING_APPROVALS[session_id]

            return (
                "Termination cancelled.\n\n"
                f"PID: {pending['pid']}\n"
                f"Process: {pending['process']}\n"
                f"CPU: {pending['cpu']}%\n\n"
                "No process was terminated."
            )


    # ======================================================
    # AUTOMATIC INCIDENT MODE
    # ======================================================

    if session_id == "incident":

        return run_incident_agent(
            user_message,
            session_id,
            previous_response_id
        )


    # ======================================================
    # NORMAL CHAT AGENT
    # ======================================================

    return run_normal_agent(
        user_message,
        session_id,
        previous_response_id
    )


# ==========================================================
# GET PENDING APPROVAL
# Used by Flask web application
# ==========================================================

def get_pending_approval(
    session_id="incident"
):

    pending = PENDING_APPROVALS.get(
        session_id
    )

    if not pending:

        return None

    return {
        "instance_id":
            pending["instance_id"],

        "pid":
            pending["pid"],

        "process_name":
            pending["process"],

        "cpu":
            pending["cpu"],

        "approval_required":
            True
    }


# ==========================================================
# CLEAR PENDING APPROVAL
# Used after web approval/rejection
# ==========================================================

def clear_pending_approval(
    session_id="incident"
):

    if session_id in PENDING_APPROVALS:

        del PENDING_APPROVALS[
            session_id
        ]


# ==========================================================
# AUTOMATIC INCIDENT AGENT
# ==========================================================

def run_incident_agent(
    user_message,
    session_id,
    previous_response_id
):

    print()
    print("=" * 40)
    print("AUTOMATIC INCIDENT AGENT")
    print("=" * 40)


    # ======================================================
    # SYSTEM INSTRUCTIONS
    # ======================================================

    system_prompt = """

You are an AWS DevOps Incident Response Agent.

An AWS monitoring system has detected an incident.

Your job is to investigate the incident using the
available AWS tools.

IMPORTANT RULES:

1. Analyze the actual incident information provided
   by the monitoring system.

2. Determine what AWS resource is affected.

3. Determine what type of problem has occurred.

4. Choose the AWS tools that are relevant to the
   incident.

5. Use actual AWS tool results as evidence.

6. Do not invent AWS information.

7. Investigate before making conclusions.

8. You may perform READ-ONLY investigation.

9. NEVER execute destructive remediation automatically.

10. NEVER terminate a process automatically.

11. If remediation appears necessary, explain what
    remediation would be appropriate and request
    human approval.

12. The same agent must be able to investigate different
    AWS services such as EC2, S3, RDS, Lambda, ECS,
    CloudWatch, and other services when appropriate.

13. Do not assume every incident is an EC2 incident.

14. Select tools based on the actual incident.

15. Produce a clear incident investigation report.

The available tools are your AWS investigation toolbox.

Use the tools intelligently rather than following a
hard-coded workflow.

"""


    # ======================================================
    # FIRST REQUEST
    # ======================================================

    input_messages = [

        {
            "role": "system",
            "content": system_prompt
        },

        {
            "role": "user",
            "content": user_message
        }

    ]


    print()
    print("Sending incident to GPT-OSS...")


    if previous_response_id:

        response = client.responses.create(

            model="openai.gpt-oss-120b",

            previous_response_id=
                previous_response_id,

            input=input_messages,

            tools=TOOL_DEFINITIONS

        )

    else:

        response = client.responses.create(

            model="openai.gpt-oss-120b",

            input=input_messages,

            tools=TOOL_DEFINITIONS

        )


    # ======================================================
    # TOOL LOOP
    # ======================================================

    return process_tool_loop(

        response,

        session_id,

        incident_mode=True

    )


# ==========================================================
# NORMAL AGENT
# ==========================================================

def run_normal_agent(
    user_message,
    session_id,
    previous_response_id
):

    print()
    print("=" * 40)
    print("NORMAL AGENT")
    print("=" * 40)


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

    return process_tool_loop(

        response,

        session_id,

        incident_mode=False

    )


# ==========================================================
# COMMON TOOL LOOP
# ==========================================================

def process_tool_loop(
    response,
    session_id,
    incident_mode=False
):

    while True:

        tool_outputs = []


        # ==================================================
        # PROCESS MODEL OUTPUT
        # ==================================================

        for item in response.output:

            if item.type != "function_call":

                continue


            print()
            print(
                f"Agent requested tool: "
                f"{item.name}"
            )


            # ------------------------------------------------
            # Parse arguments
            # ------------------------------------------------

            try:

                arguments = json.loads(
                    item.arguments or "{}"
                )

            except json.JSONDecodeError:

                print(
                    "ERROR: Invalid tool arguments"
                )

                arguments = {}


            print(
                f"Tool arguments: "
                f"{arguments}"
            )


            # =================================================
            # SAFETY BOUNDARY
            # =================================================

            if item.name == "terminate_process":

                print()
                print(
                    "BLOCKED: terminate_process "
                    "requires human approval."
                )


                result = {

                    "status":
                        "blocked",

                    "reason":
                        "terminate_process requires explicit human approval."

                }


            else:

                # ------------------------------------------------
                # Execute read-only / investigation tool
                # ------------------------------------------------

                result = execute_tool(

                    item.name,

                    arguments

                )


            print()
            print("AWS TOOL RESULT:")
            print(result)


            # =================================================
            # DETECT TOP PROCESS
            # =================================================

            if (

                item.name == "get_top_processes"

                and isinstance(
                    result,
                    dict
                )

            ):

                instance_id = arguments.get(
                    "instance_id"
                )


                top_process = extract_top_process(
                    result
                )


                if (

                    instance_id

                    and top_process

                ):

                    store_pending_approval(

                        session_id,

                        instance_id,

                        top_process

                    )


            # ------------------------------------------------
            # Send tool result back to model
            # ------------------------------------------------

            tool_outputs.append({

                "type":
                    "function_call_output",

                "call_id":
                    item.call_id,

                "output":
                    json.dumps(result)

            })


        # ==================================================
        # AGENT FINISHED
        # ==================================================

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


            report = response.output_text


            # ------------------------------------------------
            # APPROVAL EXISTS
            # ------------------------------------------------

            if session_id in PENDING_APPROVALS:

                pending = PENDING_APPROVALS[
                    session_id
                ]


                report += (

                    "\n\n"

                    "----------------------------------------\n"

                    "HUMAN APPROVAL REQUIRED\n"

                    "----------------------------------------\n\n"

                    "The investigation identified a "
                    "high CPU-consuming process.\n\n"

                    f"Instance: "
                    f"{pending['instance_id']}\n"

                    f"PID: "
                    f"{pending['pid']}\n"

                    f"Process: "
                    f"{pending['process']}\n"

                    f"CPU: "
                    f"{pending['cpu']}%\n\n"

                    "Do you want to terminate this process?\n\n"

                    "Reply YES to terminate it.\n"

                    "Reply NO to leave it running.\n"

                )


                # ==================================================
                # IMPORTANT:
                # RETURN STRUCTURED DATA FOR INCIDENT MODE
                # ==================================================

                if incident_mode:

                    return {

                        "answer":
                            report,

                        "approval_required":
                            True,

                        "instance_id":
                            pending["instance_id"],

                        "pid":
                            pending["pid"],

                        "process_name":
                            pending["process"],

                        "cpu":
                            pending["cpu"]

                    }


            # ==================================================
            # NORMAL CHAT
            # ==================================================

            return report


        # ==================================================
        # SEND TOOL RESULTS BACK TO GPT-OSS
        # ==================================================

        response = client.responses.create(

            model="openai.gpt-oss-120b",

            previous_response_id=
                response.id,

            input=tool_outputs,

            tools=TOOL_DEFINITIONS

        )


# ==========================================================
# STORE PENDING APPROVAL
# ==========================================================

def store_pending_approval(
    session_id,
    instance_id,
    top_process
):

    pid = top_process["pid"]

    process = top_process["process"]

    cpu = top_process["cpu"]


    PENDING_APPROVALS[session_id] = {

        "instance_id":
            instance_id,

        "pid":
            pid,

        "process":
            process,

        "cpu":
            cpu

    }


    print()
    print("=" * 40)
    print("HUMAN APPROVAL REQUIRED")
    print("=" * 40)


    print(
        f"Instance: {instance_id}"
    )

    print(
        f"PID: {pid}"
    )

    print(
        f"Process: {process}"
    )

    print(
        f"CPU: {cpu}%"
    )


# ==========================================================
# EXTRACT TOP PROCESS
# ==========================================================

def extract_top_process(
    top_processes
):

    if not isinstance(
        top_processes,
        dict
    ):

        return None


    stdout = top_processes.get(
        "stdout",
        ""
    )


    if not stdout:

        return None


    lines = stdout.splitlines()

    processes = []


    # ======================================================
    # Parse process rows
    # ======================================================

    for line in lines:

        line = line.strip()


        if not line:

            continue


        if line.startswith("PID"):

            continue


        parts = line.split()


        # Expected:

        # PID PPID USER %CPU %MEM ELAPSED COMMAND COMMAND...


        if len(parts) < 7:

            continue


        try:

            pid = int(
                parts[0]
            )

            cpu = float(
                parts[3]
            )

        except (
            ValueError,
            IndexError
        ):

            continue


        process_name = parts[6]


        processes.append({

            "pid":
                pid,

            "cpu":
                cpu,

            "process":
                process_name

        })


    if not processes:

        return None


    # ======================================================
    # Highest CPU first
    # ======================================================

    processes.sort(

        key=lambda x:
            x["cpu"],

        reverse=True

    )


    return processes[0]


# ==========================================================
# TERMINATION RESULT
# ==========================================================

def format_termination_result(
    pending,
    result
):

    pid = pending["pid"]

    process = pending["process"]

    cpu = pending["cpu"]


    status = result.get(
        "status"
    )


    stdout = result.get(
        "stdout",
        ""
    )


    stderr = result.get(
        "stderr",
        ""
    )


    # ======================================================
    # PROCESS TERMINATED
    # ======================================================

    if (
        "PROCESS_TERMINATION_SENT"
        in stdout
    ):

        return (

            "Human approval received.\n\n"

            "Process termination command was sent "
            "through AWS Systems Manager.\n\n"

            f"PID: {pid}\n"

            f"Process: {process}\n"

            f"Previous CPU: {cpu}%\n\n"

            f"SSM status: {status}\n\n"

            "The process termination command "
            "was executed."

        )


    # ======================================================
    # PROCESS NOT FOUND
    # ======================================================

    if (
        "PROCESS_NOT_FOUND"
        in stdout
    ):

        return (

            "Human approval received.\n\n"

            f"PID: {pid}\n"

            f"Process: {process}\n\n"

            "The process was not found when the "
            "termination command executed.\n\n"

            "It may have already exited."

        )


    # ======================================================
    # OTHER RESULT
    # ======================================================

    return (

        "Human approval received.\n\n"

        f"PID: {pid}\n"

        f"Process: {process}\n\n"

        f"SSM status: {status}\n\n"

        f"stdout:\n{stdout}\n\n"

        f"stderr:\n{stderr}"

    )
