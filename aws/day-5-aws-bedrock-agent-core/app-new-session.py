```python
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
# Create New AgentCore Session
# ============================================================

@app.route(
    "/new-session",
    methods=["POST"]
)
def new_session():

    try:

        # ----------------------------------------------------
        # Generate a completely new session ID
        # ----------------------------------------------------

        session_id = str(
            uuid.uuid4()
        )


        print()
        print("=" * 70)
        print("NEW AGENTCORE SESSION")
        print("=" * 70)

        print(
            "Session ID:",
            session_id
        )

        print("=" * 70)
        print()


        return jsonify({

            "session_id":
                session_id

        })


    except Exception as e:

        app.logger.exception(
            "Failed to create new session"
        )


        return jsonify({

            "error":
                str(e)

        }), 500


# ============================================================
# Extract text from AgentCore SSE stream
# ============================================================

def extract_agentcore_text(response):

    stream = response.get(
        "response"
    )


    if stream is None:

        print(
            "ERROR: AgentCore response stream is None"
        )

        return ""


    answer = []


    print()
    print("=" * 70)
    print("RAW AGENTCORE SSE EVENTS")
    print("=" * 70)


    # ========================================================
    # Read AgentCore SSE stream
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
        # DEBUG
        # ----------------------------------------------------

        print(
            "RAW SSE:",
            repr(line)
        )


        # ----------------------------------------------------
        # Ignore non-data SSE lines
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
        # Parse JSON
        # ----------------------------------------------------

        try:

            event = json.loads(
                json_data
            )


        except json.JSONDecodeError as e:

            print(
                "JSON PARSE ERROR:",
                e
            )

            print(
                "JSON DATA:",
                json_data
            )

            continue


        # ----------------------------------------------------
        # DEBUG EVENT
        # ----------------------------------------------------

        print(
            "PARSED EVENT:",
            json.dumps(
                event,
                indent=2
            )
        )


        # ----------------------------------------------------
        # Get event body
        # ----------------------------------------------------

        event_body = event.get(
            "event"
        )


        if not event_body:

            continue


        # ====================================================
        # contentBlockDelta
        # ====================================================

        content_block_delta = event_body.get(
            "contentBlockDelta"
        )


        if content_block_delta:

            delta = content_block_delta.get(
                "delta"
            )


            if delta:

                text = delta.get(
                    "text"
                )


                if text:

                    print(
                        "TEXT CHUNK:",
                        repr(text)
                    )


                    answer.append(
                        text
                    )


        # ====================================================
        # messageStop
        # ====================================================

        message_stop = event_body.get(
            "messageStop"
        )


        if message_stop:

            print(
                "MESSAGE STOP:",
                message_stop
            )


        # ====================================================
        # Metadata
        # ====================================================

        metadata = event_body.get(
            "metadata"
        )


        if metadata:

            print(
                "METADATA:",
                json.dumps(
                    metadata,
                    indent=2
                )
            )


    print(
        "=" * 70
    )

    print(
        "END RAW AGENTCORE SSE EVENTS"
    )

    print(
        "=" * 70
    )


    # ========================================================
    # Combine response
    # ========================================================

    final_answer = "".join(
        answer
    )


    print()
    print(
        "EXTRACTED ANSWER:",
        repr(final_answer)
    )


    return final_answer


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
        # Get JSON
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


        if not isinstance(
            prompt,
            str
        ):

            return jsonify({

                "error":
                    "Message must be a string"

            }), 400


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
        # Invoke AgentCore
        # ====================================================

        print()
        print("=" * 70)
        print("CALLING AGENTCORE")
        print("=" * 70)


        print(
            "Runtime ARN:",
            AGENT_RUNTIME_ARN
        )


        print(
            "Session ID:",
            session_id
        )


        print(
            "Prompt:",
            prompt
        )


        print(
            "=" * 70
        )


        response = agentcore.invoke_agent_runtime(

            agentRuntimeArn=
                AGENT_RUNTIME_ARN,

            runtimeSessionId=
                session_id,

            payload=
                payload,

            qualifier=
                "DEFAULT",

        )


        # ====================================================
        # AgentCore response information
        # ====================================================

        print()
        print("=" * 70)
        print("AGENTCORE RESPONSE")
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


        print(
            "=" * 70
        )


        # ====================================================
        # Extract AI response
        # ====================================================

        answer = extract_agentcore_text(
            response
        )


        # ====================================================
        # Final response
        # ====================================================

        print()
        print("=" * 70)
        print("FINAL AI RESPONSE")
        print("=" * 70)


        print(
            repr(answer)
        )


        print(
            "=" * 70
        )

        print()


        # ====================================================
        # Return response to browser
        # ====================================================

        return jsonify({

            "session_id":
                session_id,

            "response":
                answer,

        })


    except Exception as e:

        # ====================================================
        # Error handling
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
```
