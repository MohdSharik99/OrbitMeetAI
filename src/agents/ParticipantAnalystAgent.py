from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
from typing import List, Optional
import json
import uuid
from src.utils.pydantic_schemas import UsersAnalysis, UserSummary



SYSTEM_PROMPT = """
You are a Meeting Analysis expert Agent for Leadership management.
You take a meeting transcript (any format) as input and produce a structured analysis.
Use the available tools whenever the transcript or task requires them, following each tool’s 
description and intended purpose.

Workflow:
1. Analyze the transcript for each participant and extract:
   - Key updates (max 5)
   - Roadblocks (max 5)
   - Actionable items (max 5)

Return ONLY valid JSON matching this exact schema:

[
  {
    "participant_name": "John Doe",
    "key_updates": ["u1", "u2"],
    "roadblocks": ["b1"],
    "actionable": ["a1", "a2"]
  }
]
"""


class ParticipantSummaryAnalyst:
    def __init__(self, model, tools: List[BaseTool]):
        self.model = model

        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )

    async def aparticipant_analysis(self, input_transcript: str) -> List[UserSummary]:
        """
        Async version that returns List[UserSummary].

        Expected model JSON output:
        [
          {
            "participant_name": "John Doe",
            "key_updates": ["u1", "u2"],
            "roadblocks": ["b1"],
            "actionable": ["a1"]
          },
          ...
        ]
        """

        user_message = HumanMessage(content=input_transcript)

        # Async agent execution
        result = await self.agent.ainvoke(
            {"messages": user_message},
            context={"user_role": "expert_participant_analyst"}
        )

        # Extract the AIMessage text
        ai_text = next(
            m.content for m in result["messages"]
            if m.__class__.__name__ == "AIMessage"
        )

        raw_list = json.loads(ai_text)

        # Convert JSON into strongly typed UserSummary objects
        participant_summaries = []
        for u in raw_list:
            participant_summaries.append(
                UserSummary(
                    participant_name=u.get("participant_name", ""),
                    key_updates=u.get("key_updates", [])[:5],
                    roadblocks=u.get("roadblocks", [])[:5],
                    actionable=u.get("actionable", [])[:5],
                )
            )

        return participant_summaries
