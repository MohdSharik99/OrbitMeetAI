import uuid
from typing import List, Optional
from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage



PROJECT_SUMMARY_SYSTEM_PROMPT = """
You are an Executive-Level Project Analysis Agent.

Your goal: Produce a CEO-ready project summary that focuses on
ACHIEVEMENTS, ROADBLOCKS, RISKS, and OVERALL MOMENTUM.

You will receive ALL project data through the tool `fetch_project_data_from_mongo`.
Use ONLY this data. Never hallucinate.

OUTPUT FORMAT (follow exactly):

Project Name: <project name>

Participants (bold smaller font):
<name1>, <name2>, <name3>

Summary:

Meeting 1: <Meeting Name>   <Meeting Date & Time>
Achievements:
• achievement 1
• achievement 2
Roadblocks:
• blocker 1
• blocker 2
Key Notes:
• 2–3 crisp bullets summarizing the meeting

Meeting 2: <Meeting Name>   <Meeting Date & Time>
Achievements:
• ...
Roadblocks:
• ...
Key Notes:
• ...

(continue for all meetings)

Overall Progress (CEO Focused):
• 3–5 bullet points highlighting major achievements
• 2–3 bullet points summarizing key blockers or risks
• Overall confidence or momentum statement (based on data only)

RULES:
1. Achievements = measurable progress, decisions, completed tasks, or momentum.
2. Roadblocks = blockers, dependencies, delays, unresolved items.
3. Derive achievements/roadblocks using both:
   - meeting summaries
   - user_analysis entries (key_updates, roadblocks, actionable)
4. Be concise, factual, and executive-ready.
5. No JSON. Output clean formatted text.
6. Never create information not present in the project data.
"""



class ProjectSummaryAnalyst:
    def __init__(
        self,
        model,
        tools: List[BaseTool],
        project_id: Optional[uuid.UUID] = None,
    ):
        self.model = model
        self.project_id = project_id

        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=PROJECT_SUMMARY_SYSTEM_PROMPT
        )

    def generate_project_summary(self, project_id: str) -> str:
        """
        Agent uses the tool fetch_project_data_from_mongo(project_id)
        to retrieve ALL project data and generate a CEO-level summary.
        """

        user_message = HumanMessage(
            content=f"Generate a CEO-level project summary for project_id: {project_id}"
        )

        response = self.agent.invoke(
            {"messages": user_message},
            context={"user_role": "executive_analyst"}
        )

        final_output = [
            m.content for m in response["messages"]
            if m.__class__.__name__ == "AIMessage"
        ][0]

        return final_output
