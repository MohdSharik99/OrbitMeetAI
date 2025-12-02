from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_core.stores import BaseStore

from typing import List
import json

# importing pydantic schemas
from src.utils.pydantic_schemas import UserAnalysis

# System prompt - simple and direct
SYSTEM_PROMPT = """You are a Meeting Analysis Agent.
You take a meeting transcript (any format) as input and produce a structured analysis in MeetingAnalysis format.

Workflow:
1. If the input is a file, use format_normalize_tool to extract and normalize text.
2. Convert the transcript to ORBIT MEET or MS Teams format using orbit_meet_tool.
3. Analyze transcript for each participant by identifying key updates, roadblocks, and actionable items.

Return ONLY JSON in this exact UserAnalysis pydantic object format:
[
  {
    "participant_name": "John Doe",
    "key_updates": ["update1", "update2", "update3"],
    "roadblocks": ["block1", "block2", "block3"],
    "actionable": ["action1", "action2", "action3", "action4", "action5"]
  }
]
"""


class UserAnalysisAgent:
    def __init__(self, llm, tools: List[BaseTool]):
        self.llm = llm
        self.agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )

    def analyze_users(self, input_transcript: str) -> List[UserAnalysis]:
        try:
            # Correct HumanMessage initialization
            # user_message = HumanMessage(content=input_transcript)

            # Agent requires {"messages": [...]}
            result = self.agent.invoke([input_transcript])


            # result is like {"output": "...json..."}
            output_text = result.get("output", "[]")

            # Parse JSON
            user_data = json.loads(output_text)
            user_analyses = []

            for user in user_data:
                user_analyses.append(
                    UserAnalysis(
                        participant_name=user["participant_name"],
                        key_updates=user["key_updates"][:5],
                        roadblocks=user["roadblocks"][:5],
                        actionable=user["actionable"][:5]
                    )
                )

            return user_analyses

        except Exception as e:
            print("Error in User Analysis:", e)
            return []


