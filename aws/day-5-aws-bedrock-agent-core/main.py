import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel


app = BedrockAgentCoreApp()

MODEL_ID = os.getenv(
    "MODEL_ID",
    "openai.gpt-5.6-luna"
)

AWS_REGION = os.getenv(
    "AWS_REGION",
    "us-east-1"
)


model = BedrockModel(
    model_id=MODEL_ID,
    region_name=AWS_REGION
)


agent = Agent(
    model=model,
    system_prompt="""
You are a helpful AWS DevOps Agent.

You help engineers understand AWS, DevOps,
Kubernetes, EC2, CloudWatch, CI/CD and
production incidents.

Answer clearly and accurately.

Do not invent information about the user's
AWS infrastructure.
"""
)


@app.entrypoint
def invoke(payload):

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
            "message": "Please enter a message."
        }

    response = agent(prompt)

    return {
        "message": response.message
    }


if __name__ == "__main__":
    app.run()
