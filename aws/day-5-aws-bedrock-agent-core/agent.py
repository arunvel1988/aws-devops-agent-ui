import json
import logging
import boto3

from bedrock_agentcore import BedrockAgentCoreApp


# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# AgentCore application
# --------------------------------------------------

app = BedrockAgentCoreApp()


# --------------------------------------------------
# AWS Bedrock
# --------------------------------------------------

REGION = "us-east-1"

MODEL_ID = "openai.gpt-5.6-luna"

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=REGION
)


# --------------------------------------------------
# AgentCore entrypoint
# --------------------------------------------------

@app.entrypoint
def invoke(payload):

    logger.info("Received payload: %s", payload)

    # ----------------------------------------------
    # Extract prompt
    # ----------------------------------------------

    if isinstance(payload, dict):
        prompt = (
            payload.get("prompt")
            or payload.get("input")
            or ""
        )

    elif isinstance(payload, str):
        prompt = payload

    else:
        prompt = ""

    if not prompt:
        return {
            "message": "Please provide a prompt."
        }

    logger.info("Prompt: %s", prompt)

    # ----------------------------------------------
    # Call Bedrock
    # ----------------------------------------------

    try:

        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        # ------------------------------------------
        # Extract model response
        # ------------------------------------------

        message = response["output"]["message"]

        text = message["content"][0]["text"]

        logger.info("Model response: %s", text)

        return {
            "message": text
        }

    except Exception as e:

        logger.exception(
            "Bedrock invocation failed"
        )

        return {
            "message": f"Bedrock error: {str(e)}"
        }


# --------------------------------------------------
# Run AgentCore application
# --------------------------------------------------

if __name__ == "__main__":
    app.run()
