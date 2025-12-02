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

class UserAnalysisAgent:
    def __init__(self, model, tools: List[BaseTool],
                 project_id: Optional[uuid.UUID] = None,
                 meeting_id: Optional[uuid.UUID] = None):
        self.model = model
        self.project_id = project_id
        self.meeting_id = meeting_id

        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

    def participant_analysis(self, input_transcript: str) -> str:
        """
        Uses LLM to generate participant analysis JSON.

        Returns:
            str : JSON output from model.
        """
        user_message = HumanMessage(content=input_transcript)

        result = self.agent.invoke(
            {"messages": user_message},
            context={"user_role": "expert"}
        )

        # result is ALWAYS {"output": "...json..."}
        output_text = [
            m.content for m in result["messages"]
            if m.__class__.__name__ == "AIMessage"][0]

        return output_text

    def parse_output_to_schema(self, text: str) -> List[UsersAnalysis]:
        """
        Converts JSON output into schema objects.

        Returns:
            List[UserAnalysis]
        """
        data = json.loads(text)
        participant_analysis = []

        for user in data:
            summary = UserSummary(
                participant_name=user.get("participant_name", ""),
                key_updates=user.get("key_updates", [])[:5],
                roadblocks=user.get("roadblocks", [])[:5],
                actionable=user.get("actionable", [])[:5],
            )

            participant_analysis.append(
                UsersAnalysis(
                    project_id=self.project_id,
                    meeting_id=self.meeting_id,
                    participant_summary=summary
                )
            )

        return participant_analysis