from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
from typing import List, Optional
import json
import uuid
from langchain_core.output_parsers import JsonOutputParser

from src.utils.pydantic_schemas import SummaryList





SYSTEM_PROMPT = """
You are a Meeting Analysis expert Agent for Leadership management.

Your task: Read the meeting transcript exactly as given and produce a concise factual summary. 
Use the available tools whenever the transcript or task requires them, following each tool’s 
description and intended purpose.

GUIDELINES:
1. Base every summary point only on information that explicitly appears in the transcript.
2. When something is unclear or incomplete in the transcript, describe it as unclear.
3. Keep all points factual, concise, and directly taken from what participants said.
4. Preserve meaning without adding interpretations, assumptions, or conclusions.
5. Avoid combining unrelated points unless the transcript clearly connects them.
6. Use the speaker’s exact content as the only source for the summary.


OUTPUT FORMAT:
Return a valid JSON list of 8–10 bullet points (strings).  
Example structure:

[
  "Speaker A shared progress on the project timeline",
  "Speaker B mentioned a blocker related to staging access",
  "The team aligned on the next steps"
]

If the transcript includes fewer than 8 meaningful points, return only the available points.  
If the transcript includes more than 10 meaningful points, select the most important ones.

"""


class MeetingSummaryAnalyst:
    def __init__(self, model, tools: List[BaseTool],
                 project_id: Optional[uuid.UUID] = None,
                 meeting_id: Optional[uuid.UUID] = None):

        self.model = model
        self.project_id = project_id
        self.meeting_id = meeting_id

        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )

    def generate_summary(self, input_transcript: str) -> SummaryList:
        user_message = HumanMessage(content=input_transcript)

        response = self.agent.invoke(
            {"messages": user_message},
            context={"user_role": "expert"}
        )

        # Extract AI message text
        output_text = [
            m.content for m in response["messages"]
            if m.__class__.__name__ == "AIMessage"][0]

        # Parse JSON list from model output
        parser = JsonOutputParser()
        summary_points = parser.parse(output_text)

        # Return schema object
        return SummaryList(
            project_id=self.project_id,
            meeting_id=self.meeting_id,
            summary_points=summary_points
        )