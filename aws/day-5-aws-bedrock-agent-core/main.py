from typing import Any
from collections import OrderedDict

from strands import Agent, tool
from strands.agent.conversation_manager.null_conversation_manager import (
    NullConversationManager,
)

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client


# ============================================================
# AgentCore Runtime
# ============================================================

app = BedrockAgentCoreApp()
log = app.logger


# ============================================================
# System Prompt
# ============================================================

DEFAULT_SYSTEM_PROMPT = """
You are an AWS DevOps Agent.

You help users with:

- AWS
- EC2
- SSM
- Docker
- Linux
- Kubernetes
- CloudWatch
- Monitoring
- Troubleshooting
- Infrastructure
- Security
- DevOps
- CI/CD

You have access to tools through MCP.

IMPORTANT BEHAVIOR:

1. For normal questions, answer directly using the language model.
2. Use MCP tools when the request requires real-time information
   from infrastructure or external systems.
3. Do not call tools unnecessarily.
4. When a tool is required, select the most appropriate tool.
5. Analyze the tool result before responding to the user.
6. Clearly explain the result to the user.
7. Do not invent infrastructure information when a tool can provide
   the actual information.
8. For potentially destructive operations, understand the user's
   request carefully before executing them.

You are running as an agent inside Amazon Bedrock AgentCore Runtime.
"""


# ============================================================
# Tools
# ============================================================

tools = []


# ------------------------------------------------------------
# Example local function tool
# ------------------------------------------------------------

@tool
def add_numbers(a: int, b: int) -> int:
    """
    Return the sum of two numbers.
    """
    return a + b


tools.append(add_numbers)


# ============================================================
# MCP Clients
# ============================================================

# Your existing MCP client.
#
# This connects the AgentCore agent to your MCP server.
#
# If the MCP server is available, its tools are added to the
# Strands Agent.
#
# If the MCP server is unavailable, the agent can still work
# as a normal chat agent using the Bedrock model.

mcp_clients = [
    get_streamable_http_mcp_client()
]


# ------------------------------------------------------------
# Add MCP clients to the agent tools
# ------------------------------------------------------------

for mcp_client in mcp_clients:

    if mcp_client:

        tools.append(mcp_client)

        log.info(
            "MCP client added to agent."
        )


# ============================================================
# Conversation Manager
# ============================================================

def _make_conversation_manager():
    """
    Creates the conversation manager used by each Agent instance.
    """

    return NullConversationManager()


# ============================================================
# Session-based Agent Cache
# ============================================================

def agent_factory():

    # Keep separate Agent objects for separate sessions.
    cache = OrderedDict()

    def get_or_create_agent(session_id):

        # ----------------------------------------------------
        # Existing session
        # ----------------------------------------------------

        if session_id in cache:

            cache.move_to_end(session_id)

            return cache[session_id]


        # ----------------------------------------------------
        # Limit number of sessions in memory
        # ----------------------------------------------------

        if len(cache) >= 128:

            cache.popitem(
                last=False
            )


        # ----------------------------------------------------
        # Create new Strands Agent
        # ----------------------------------------------------

        log.info(
            f"Creating new agent for session: {session_id}"
        )

        agent = Agent(

            # Bedrock model
            model=load_model(),

            # System prompt
            system_prompt=DEFAULT_SYSTEM_PROMPT,

            # Local + MCP tools
            tools=tools,

            # Conversation manager
            conversation_manager=_make_conversation_manager(),

            # Hooks
            hooks=[],
        )


        # Store agent for this session

        cache[session_id] = agent

        return agent


    return get_or_create_agent


get_or_create_agent = agent_factory()


# ============================================================
# Message Processing
# ============================================================

def strip_trailing_tool_use(
    messages: Any,
) -> list[dict]:

    """
    Remove trailing toolUse blocks from the tail of the
    conversation when required by the AgentCore runtime
    harness.
    """

    if not isinstance(messages, list):

        raise ValueError(
            "messages must be a list"
        )


    messages = list(messages)


    while messages:

        last = messages[-1]


        if not isinstance(last, dict):

            raise ValueError(
                "each message must be an object"
            )


        original_content = last.get(
            "content",
            [],
        )


        if (
            not isinstance(
                original_content,
                list,
            )
            or not all(
                isinstance(block, dict)
                for block in original_content
            )
        ):

            raise ValueError(
                "each message content value must be "
                "a list of content blocks"
            )


        content = [
            block
            for block in original_content
            if "toolUse" not in block
        ]


        # Nothing to remove

        if len(content) == len(
            original_content
        ):

            break


        # Some content remains

        if content:

            messages[-1] = {
                **last,
                "content": content,
            }

            break


        # Entire message was toolUse

        messages.pop()


    return messages


# ============================================================
# Extract Prompt
# ============================================================

def _extract_prompt(
    payload: dict,
):

    """
    Accepts:

    1. Normal prompt

       {
           "prompt": "Hello"
       }

    2. AgentCore messages

       {
           "messages": [...]
       }

    3. Tool results

       {
           "tool_results": [...]
       }
    """

    if not isinstance(payload, dict):

        raise ValueError(
            "payload must be a JSON object"
        )


    # --------------------------------------------------------
    # AgentCore / harness messages
    # --------------------------------------------------------

    if "messages" in payload:

        return strip_trailing_tool_use(
            payload["messages"]
        )


    # --------------------------------------------------------
    # Tool results
    # --------------------------------------------------------

    if "tool_results" in payload:

        tool_results = payload[
            "tool_results"
        ]


        if (
            not isinstance(
                tool_results,
                list,
            )
            or not all(
                isinstance(
                    tool_result,
                    dict,
                )
                and isinstance(
                    tool_result.get(
                        "toolUseId"
                    ),
                    str,
                )
                for tool_result
                in tool_results
            )
        ):

            raise ValueError(
                "tool_results must contain objects "
                "with a toolUseId string"
            )


        return [
            {
                "role": "user",

                "content": [

                    {
                        "toolResult": {

                            "toolUseId": tr[
                                "toolUseId"
                            ],

                            "status": tr.get(
                                "status",
                                "success",
                            ),

                            "content": tr.get(
                                "content",
                                [],
                            ),
                        }
                    }

                    for tr in tool_results
                ],
            }
        ]


    # --------------------------------------------------------
    # Normal chat prompt
    # --------------------------------------------------------

    prompt = payload.get(
        "prompt",
        "",
    )


    if not isinstance(
        prompt,
        str,
    ):

        raise ValueError(
            "prompt must be a string"
        )


    return prompt


# ============================================================
# Runtime Entrypoint
# ============================================================

@app.entrypoint
async def invoke(
    payload,
    context,
):

    log.info(
        "Invoking AWS DevOps Agent..."
    )


    # --------------------------------------------------------
    # Get AgentCore session ID
    # --------------------------------------------------------

    session_id = getattr(
        context,
        "session_id",
        "default-session",
    )


    log.info(
        f"Session ID: {session_id}"
    )


    # --------------------------------------------------------
    # Get / create agent for this session
    # --------------------------------------------------------

    agent = get_or_create_agent(
        session_id
    )


    # --------------------------------------------------------
    # Extract user prompt
    # --------------------------------------------------------

    prompt = _extract_prompt(
        payload
    )


    log.info(
        f"Prompt received: {prompt}"
    )


    # --------------------------------------------------------
    # Stream Agent response
    # --------------------------------------------------------

    async for event in agent.stream_async(
        prompt
    ):

        # Make sure event is a dictionary

        if not isinstance(
            event,
            dict,
        ):

            continue


        # Only process AgentCore events

        if "event" not in event:

            continue


        event_data = event[
            "event"
        ]


        # ----------------------------------------------------
        # Handle contentBlockStart
        # ----------------------------------------------------

        content_block_start = event_data.get(
            "contentBlockStart"
        )


        if (
            content_block_start is not None
            and not content_block_start.get(
                "start"
            )
        ):

            continue


        # ----------------------------------------------------
        # Send event to AgentCore Runtime
        # ----------------------------------------------------

        yield event


# ============================================================
# Local Development
# ============================================================

if __name__ == "__main__":

    app.run()
