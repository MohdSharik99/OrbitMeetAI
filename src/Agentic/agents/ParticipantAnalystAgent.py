from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage
from typing import List
import json
import re

from src.Agentic.utils.pydantic_schemas import UserSummary


SYSTEM_PROMPT = """
You are a professional Meeting Analysis expert Agent for Leadership of the organization.

Your ONLY job:
Return participant-wise analysis in STRICT JSON format very effective and concise tone.

RULES:
1. Output ONLY a JSON array. Nothing else.
2. Do NOT include markdown (no ```json).
3. No explanations.
4. JSON schema:

[
  {
    "participant_name": "John Doe",
    "key_updates": ["u1", "u2"],
    "roadblocks": ["b1"],
    "actionable": ["a1"]
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

    # ---------------------------------------------------------
    # Helper to clean markdown wrappers like ```json ... ```
    # ---------------------------------------------------------
    def _strip_markdown(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^```", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        return text

    # ---------------------------------------------------------
    # Helper to attempt JSON repair if malformed
    # ---------------------------------------------------------
    def _attempt_json_fix(self, text: str) -> str:
        # Remove any trailing commas, unmatched brackets, etc.
        text = text.strip()

        # If content ends with ",", remove it
        text = re.sub(r",\s*]", "]", text)
        text = re.sub(r",\s*}", "}", text)

        # In case extra comments/explanations remain, try extracting JSON array
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if match:
            return match.group(0).strip()

        return text

    # ---------------------------------------------------------
    # Main async inference
    # ---------------------------------------------------------
    async def aparticipant_analysis(self, input_transcript: str) -> List[UserSummary]:

        user_message = HumanMessage(content=input_transcript)

        # Call agent
        result = await self.agent.ainvoke(
            {"messages": user_message},
            context={"user_role": "expert_participant_analyst"}
        )

        # Extract content
        ai_msg = next(m for m in result["messages"] if isinstance(m, AIMessage))
        ai_text = ai_msg.content.strip()

        # 1. Clean markdown
        cleaned = self._strip_markdown(ai_text)

        # 2. Try JSON parse
        try:
            raw_list = json.loads(cleaned)
        except Exception:
            # Try repairing JSON automatically
            repaired = self._attempt_json_fix(cleaned)
            try:
                raw_list = json.loads(repaired)
            except Exception as e:
                raise ValueError(
                    f"LLM returned invalid JSON even after cleanup.\n"
                    f"Original:\n{ai_text}\n\nCleaned:\n{cleaned}\n\nRepaired:\n{repaired}"
                ) from e

        # Convert to pydantic objects
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
