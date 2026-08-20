from flask import Flask, render_template, request, jsonify

from agent.core import run_agent
from tools.ssm.actions import kill_process


app = Flask(__name__)


# ==================================================
# STORE LATEST AUTOMATIC INCIDENT
# ==================================================

latest_incident = {
    "available": False
}


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():

    return render_template("index.html")


# ==================================================
# CHAT API
# ==================================================

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Invalid request"
        }), 400

    message = data.get("message", "").strip()

    if not message:

        return jsonify({
            "error": "Message cannot be empty"
        }), 400

    try:

        print()
        print("========================================")
        print("AWS DEVOPS AGENT")
        print("========================================")

        print("User message:")
        print(message)

        # ------------------------------------------
        # Run Agent
        # ------------------------------------------

        answer = run_agent(
            message,
            session_id="default"
        )

        print()
        print("========================================")
        print("AGENT FINISHED")
        print("========================================")

        return jsonify({
            "answer": answer
        })

    except Exception as e:

        print()
        print("========================================")
        print("AGENT ERROR")
        print("========================================")

        print(e)

        return jsonify({
            "error": str(e)
        }), 500


# ==================================================
# AUTOMATIC INCIDENT
# CloudWatch
#     ↓
# EventBridge
#     ↓
# Flask
#     ↓
# run_agent()
# ==================================================

@app.route("/incident", methods=["POST"])
def incident():

    global latest_incident

    print()
    print("========================================")
    print("AUTOMATIC INCIDENT RECEIVED")
    print("========================================")

    # ------------------------------------------
    # Read EventBridge event
    # ------------------------------------------

    data = request.get_json(silent=True)

    if not data:

        print("No JSON event received.")

        return jsonify({
            "status": "error",
            "message": "Invalid or empty event"
        }), 400

    print("EventBridge Event:")
    print(data)

    # ------------------------------------------
    # Extract alarm information
    # ------------------------------------------

    detail = data.get("detail", {})

    alarm_name = detail.get(
        "alarmName",
        "unknown"
    )

    state = detail.get(
        "state",
        {}
    )

    state_value = state.get(
        "value",
        "unknown"
    )

    reason = state.get(
        "reason",
        ""
    )

    print()
    print("Alarm Name :", alarm_name)
    print("State      :", state_value)
    print("Reason     :", reason)

    # ------------------------------------------
    # Only process ALARM events
    # ------------------------------------------

    if state_value != "ALARM":

        print("Event is not an ALARM event.")

        return jsonify({
            "status": "ignored",
            "message": "Event is not an ALARM state"
        }), 200

    # ------------------------------------------
    # Incident detected
    # ------------------------------------------

    print()
    print("========================================")
    print("INCIDENT DETECTED")
    print("========================================")

    print(
        f"CloudWatch alarm '{alarm_name}' "
        f"is in ALARM state."
    )

    # ------------------------------------------
    # Build automatic investigation prompt
    # ------------------------------------------

    investigation_prompt = f"""
An automatic CloudWatch incident has been detected.

Alarm Name: {alarm_name}

Alarm State: {state_value}

Alarm Reason:
{reason}

Investigate this incident automatically.

Determine:
1. Which AWS resource is affected.
2. What is causing the problem.
3. Relevant CloudWatch metrics.
4. The top CPU-consuming process if this is an EC2 CPU incident.
5. Whether remediation is required.

Perform investigation using the available read-only tools.

If you identify a process that should potentially be terminated,
DO NOT terminate it automatically.

Return the investigation findings and clearly identify:

Instance ID
PID
Process Name
CPU percentage

Human approval is required before any destructive action.
"""

    # ------------------------------------------
    # Run Agent
    # ------------------------------------------

    try:

        print()
        print("========================================")
        print("STARTING AUTOMATIC AGENT")
        print("========================================")

        answer = run_agent(
            investigation_prompt,
            session_id="incident"
        )

        print()
        print("========================================")
        print("AUTOMATIC AGENT FINISHED")
        print("========================================")

        print(answer)

        # ------------------------------------------
        # Extract approval information
        #
        # IMPORTANT:
        # The agent response normally contains
        # the process information.
        #
        # For now we store the complete answer.
        # ------------------------------------------

        latest_incident = {

            "available": True,

            "alarm": alarm_name,

            "state": state_value,

            "reason": reason,

            "investigation": answer,

            "instance_id": None,

            "pid": None,

            "process_name": None,

            "cpu": None,

            "approval_required": True

        }

        print()
        print("========================================")
        print("INCIDENT STORED FOR WEB UI")
        print("========================================")

        return jsonify({

            "status":
                "incident_investigated",

            "alarm":
                alarm_name,

            "state":
                state_value,

            "investigation":
                answer,

            "approval_required":
                True

        }), 200

    except Exception as e:

        print()
        print("========================================")
        print("AUTOMATIC AGENT ERROR")
        print("========================================")

        print(e)

        latest_incident = {

            "available":
                True,

            "alarm":
                alarm_name,

            "state":
                state_value,

            "reason":
                reason,

            "investigation":
                f"Agent error: {str(e)}",

            "approval_required":
                False,

            "error":
                str(e)

        }

        return jsonify({

            "status":
                "agent_failed",

            "error":
                str(e)

        }), 500


# ==================================================
# INCIDENT STATUS
#
# Browser calls this endpoint periodically.
# ==================================================

@app.route("/incident-status", methods=["GET"])
def incident_status():

    global latest_incident

    return jsonify(latest_incident)


# ==================================================
# CLEAR INCIDENT
# ==================================================

@app.route("/incident-clear", methods=["POST"])
def incident_clear():

    global latest_incident

    latest_incident = {
        "available": False
    }

    print()
    print("========================================")
    print("INCIDENT CLEARED FROM WEB UI")
    print("========================================")

    return jsonify({
        "status": "cleared"
    })


# ==================================================
# HUMAN APPROVAL
# ==================================================

@app.route("/approve-action", methods=["POST"])
def approve_action():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Invalid request"
        }), 400

    # ------------------------------------------
    # Read approval information
    # ------------------------------------------

    approved = data.get("approved")

    instance_id = data.get("instance_id")

    pid = data.get("pid")

    print()
    print("========================================")
    print("HUMAN APPROVAL REQUEST")
    print("========================================")

    print("Approved:", approved)
    print("Instance:", instance_id)
    print("PID:", pid)

    # ------------------------------------------
    # HUMAN SAID NO
    # ------------------------------------------

    if not approved:

        print("Human rejected the action.")

        return jsonify({

            "status":
                "rejected",

            "message":
                "Action rejected by human. No changes were made."

        })

    # ------------------------------------------
    # VALIDATE INSTANCE
    # ------------------------------------------

    if not instance_id:

        return jsonify({

            "error":
                "instance_id is required"

        }), 400

    # ------------------------------------------
    # VALIDATE PID
    # ------------------------------------------

    if pid is None:

        return jsonify({

            "error":
                "pid is required"

        }), 400

    try:

        # ------------------------------------------
        # Convert PID to integer
        # ------------------------------------------

        pid = int(pid)

        # ------------------------------------------
        # Safety check
        # ------------------------------------------

        if pid <= 0:

            return jsonify({

                "error":
                    "Invalid PID"

            }), 400

        print()
        print("========================================")
        print("EXECUTING REMEDIATION")
        print("========================================")

        print(
            f"Instance ID : {instance_id}"
        )

        print(
            f"PID         : {pid}"
        )

        # ------------------------------------------
        # Execute SSM command
        # ------------------------------------------

        result = kill_process(

            instance_id,
            pid

        )

        print()
        print("SSM RESULT")
        print(result)

        # ------------------------------------------
        # Clear incident after execution
        # ------------------------------------------

        global latest_incident

        latest_incident = {
            "available": False
        }

        # ------------------------------------------
        # Return result
        # ------------------------------------------

        return jsonify({

            "status":
                "executed",

            "message":
                f"Termination command sent for PID {pid}.",

            "result":
                result

        })

    except ValueError:

        return jsonify({

            "error":
                "PID must be a number."

        }), 400

    except Exception as e:

        print()
        print("========================================")
        print("REMEDIATION ERROR")
        print("========================================")

        print(e)

        return jsonify({

            "status":
                "failed",

            "error":
                str(e)

        }), 500


# ==================================================
# START FLASK
# ==================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )
