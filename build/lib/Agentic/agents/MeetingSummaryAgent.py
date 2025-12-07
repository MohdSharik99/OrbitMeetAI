from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
from typing import List
from langchain_core.output_parsers import JsonOutputParser

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
5. Each summary point should be in 120-150 characters.
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
    def __init__(self, model, tools: List[BaseTool]):
        self.model = model

        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )

    async def agenerate_summary(self, input_transcript: str) -> List[str]:

        user_message = HumanMessage(content=input_transcript)

        # IMPORTANT: async version of agent execution
        response = await self.agent.ainvoke(
            {"messages": user_message},
            context={"user_role": "expert_meeting_analyst"}
        )

        # Extract model output (AIMessage)
        output_text = next(
            m.content for m in response["messages"]
            if m.__class__.__name__ == "AIMessage"
        )

        # Parse JSON list of bullet points
        parser = JsonOutputParser()
        summary_points = parser.parse(output_text)

        return summary_points

