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
# Chat API
# ============================================================

@app.route(
    "/chat",
    methods=["POST"],
)
def chat():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "error": "No JSON payload received"
            }), 400


        prompt = data.get(
            "message",
            "",
        )


        if not prompt.strip():

            return jsonify({
                "error": "Message cannot be empty"
            }), 400


        # ----------------------------------------------------
        # Create / receive session ID
        # ----------------------------------------------------

        session_id = data.get(
            "session_id"
        )


        if not session_id:

            session_id = str(
                uuid.uuid4()
            )


        # ----------------------------------------------------
        # Invoke AgentCore Runtime
        # ----------------------------------------------------

        payload = json.dumps({
            "prompt": prompt
        }).encode("utf-8")


        response = agentcore.invoke_agent_runtime(

            agentRuntimeArn=AGENT_RUNTIME_ARN,

            runtimeSessionId=session_id,

            payload=payload,

            qualifier="DEFAULT",
        )


        # ----------------------------------------------------
        # AgentCore returns streaming chunks
        # ----------------------------------------------------

        chunks = []


        for chunk in response.get(
            "response",
            [],
        ):

            if isinstance(
                chunk,
                bytes,
            ):

                chunks.append(
                    chunk.decode("utf-8")
                )

            else:

                chunks.append(
                    str(chunk)
                )


        raw_response = "".join(
            chunks
        )


        # ----------------------------------------------------
        # Try JSON response
        # ----------------------------------------------------

        try:

            result = json.loads(
                raw_response
            )

        except json.JSONDecodeError:

            result = {
                "message": raw_response
            }


        # ----------------------------------------------------
        # Return response to browser
        # ----------------------------------------------------

        return jsonify({

            "session_id": session_id,

            "response": result,

        })


    except Exception as e:

        app.logger.exception(
            "AgentCore invocation failed"
        )

        return jsonify({

            "error": str(e)

        }), 500


# ============================================================
# Run Flask
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
