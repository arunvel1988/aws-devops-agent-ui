import json
import uuid

import boto3

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
)


app = Flask(__name__)


# ============================================================
# AWS Configuration
# ============================================================

AWS_REGION = "us-east-1"

AGENT_RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:"
    "us-east-1:"
    "952035287138:"
    "runtime/DevOpsAgent_DevOpsAgent-KWHNQyH8XF"
)


# ============================================================
# AgentCore Client
# ============================================================

agentcore = boto3.client(
    "bedrock-agentcore",
    region_name=AWS_REGION,
)


# ============================================================
# Chat UI
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# Extract text from AgentCore SSE stream
# ============================================================

def extract_agentcore_text(response):

    stream = response.get("response")

    if stream is None:

        return ""


    answer = []


    # ========================================================
    # AgentCore returns text/event-stream
    # ========================================================

    for line in stream.iter_lines():

        if not line:

            continue


        # ----------------------------------------------------
        # Convert bytes to string
        # ----------------------------------------------------

        if isinstance(
            line,
            bytes
        ):

            line = line.decode(
                "utf-8",
                errors="ignore"
            )


        line = line.strip()


        # ----------------------------------------------------
        # Ignore anything that isn't an SSE data line
        # ----------------------------------------------------

        if not line.startswith(
            "data:"
        ):

            continue


        # ----------------------------------------------------
        # Remove "data:"
        # ----------------------------------------------------

        json_data = line[
            5:
        ].strip()


        if not json_data:

            continue


        # ----------------------------------------------------
        # Convert JSON string into Python dictionary
        # ----------------------------------------------------

        try:

            event = json.loads(
                json_data
            )

        except json.JSONDecodeError:

            print(
                "Could not parse:",
                json_data
            )

            continue


        # ----------------------------------------------------
        # Get event
        # ----------------------------------------------------

        event_body = event.get(
            "event"
        )

        if not event_body:

            continue


        # ----------------------------------------------------
        # Get contentBlockDelta
        # ----------------------------------------------------

        content_block_delta = event_body.get(
            "contentBlockDelta"
        )

        if not content_block_delta:

            continue


        # ----------------------------------------------------
        # Get delta
        # ----------------------------------------------------

        delta = content_block_delta.get(
            "delta"
        )

        if not delta:

            continue


        # ----------------------------------------------------
        # Get actual AI text
        # ----------------------------------------------------

        text = delta.get(
            "text"
        )

        if text:

            answer.append(
                text
            )


    # ========================================================
    # Combine all chunks
    # ========================================================

    return "".join(
        answer
    )


# ============================================================
# Chat API
# ============================================================

@app.route(
    "/chat",
    methods=["POST"],
)
def chat():

    try:

        # ====================================================
        # Get request JSON
        # ====================================================

        data = request.get_json()


        if not data:

            return jsonify({

                "error":
                    "No JSON payload received"

            }), 400


        # ====================================================
        # Get user message
        # ====================================================

        prompt = data.get(
            "message",
            "",
        )


        if not prompt.strip():

            return jsonify({

                "error":
                    "Message cannot be empty"

            }), 400


        # ====================================================
        # Session ID
        # ====================================================

        session_id = data.get(
            "session_id"
        )


        if not session_id:

            session_id = str(
                uuid.uuid4()
            )


        # ====================================================
        # Create AgentCore payload
        # ====================================================

        payload = json.dumps({

            "prompt": prompt

        }).encode(
            "utf-8"
        )


        # ====================================================
        # Invoke AgentCore Runtime
        # ====================================================

        response = agentcore.invoke_agent_runtime(

            agentRuntimeArn=AGENT_RUNTIME_ARN,

            runtimeSessionId=session_id,

            payload=payload,

            qualifier="DEFAULT",

        )


        # ====================================================
        # Debug information
        # ====================================================

        print()
        print("=" * 70)
        print("AGENTCORE")
        print("=" * 70)

        print(
            "Status:",
            response.get(
                "statusCode"
            )
        )

        print(
            "Content-Type:",
            response.get(
                "contentType"
            )
        )

        print("=" * 70)
        print()


        # ====================================================
        # Extract ONLY AI text
        # ====================================================

        answer = extract_agentcore_text(
            response
        )


        # ====================================================
        # Debug final answer
        # ====================================================

        print()
        print("=" * 70)
        print("FINAL AI RESPONSE")
        print("=" * 70)
        print(answer)
        print("=" * 70)
        print()


        # ====================================================
        # Return clean response
        # ====================================================

        return jsonify({

            "session_id":
                session_id,

            "response":
                answer,

        })


    except Exception as e:

        # ====================================================
        # Log error
        # ====================================================

        app.logger.exception(
            "AgentCore invocation failed"
        )


        return jsonify({

            "error":
                str(e)

        }), 500


# ============================================================
# Run Flask
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True,

        use_reloader=False,

    )
