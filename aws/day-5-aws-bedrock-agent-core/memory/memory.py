cat memory.py 
import os
from typing import Optional

from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)

from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)


MEMORY_ID = os.getenv(
    "MEMORY_DEVOPSMEMORY_ID"
)

REGION = os.getenv(
    "AWS_REGION",
    "us-east-1"
)


def get_memory_session_manager(
    session_id: str,
    actor_id: str,
) -> Optional[AgentCoreMemorySessionManager]:

    if not MEMORY_ID:
        print(
            "AgentCore Memory ID not configured."
        )

        return None


    retrieval_config = {

        f"/facts/{actor_id}":
            RetrievalConfig(
                top_k=3,
                relevance_score=0.5,
            ),

        f"/preferences/{actor_id}":
            RetrievalConfig(
                top_k=3,
                relevance_score=0.5,
            ),

        f"/summaries/{actor_id}/{session_id}":
            RetrievalConfig(
                top_k=3,
                relevance_score=0.5,
            ),
    }


    return AgentCoreMemorySessionManager(

        AgentCoreMemoryConfig(

            memory_id=MEMORY_ID,

            session_id=session_id,

            actor_id=actor_id,

            retrieval_config=
                retrieval_config,
        ),

        REGION,
    )
