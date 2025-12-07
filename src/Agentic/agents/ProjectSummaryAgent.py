import uuid
from typing import List, Optional, Dict, Any
from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage



PROJECT_SUMMARY_SYSTEM_PROMPT = """
You are an expert business analyst producing a global project summary for executive leadership.

Your goal: synthesize ALL meetings in the project and produce a clear, CEO-level report.

STRICT OUTPUT FORMAT:
1. Project Name: <big font style section>
2. Participants: name1, name2, ...  (bold)
3. Summary: (big font)

For each meeting:

Meeting <number>: <Meeting Name> <Meeting Date & Time>
summary:
- bullet 1
- bullet 2
- bullet 3

After all meetings:

Overall Progress:
- 3–5 bullet points summarizing accomplishments, momentum, and major updates

Roadblocks:
- 2–4 bullet points (only if present)

Action Items:
- 2–4 bullets across participants (optional but encouraged)

STYLE RULES:
- Use concise professional language.
- Avoid unnecessary filler.
- Do NOT invent details not present.
- Combine recurring themes across meetings.
"""


class ProjectSummaryAnalyst:
    def __init__(self, model, tools: List, system_prompt: str = PROJECT_SUMMARY_SYSTEM_PROMPT):
        self.model = model

        self.agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt
        )

    # ---------------------------------------------------------
    # ASYNC VERSION of project summary generator
    # ---------------------------------------------------------
    async def agenerate_project_summary(self, project_data: Dict[str, Any]) -> str:
        """
        Async-only method.
        Takes entire project data and produces a CEO-level global summary.
        """

        formatted_input = self._format_project_json(project_data)
        user_message = HumanMessage(content=formatted_input)

        # Async LLM execution
        response = await self.agent.ainvoke(
            {"messages": user_message},
            context={"user_role": "executive_report"}
        )

        # Extract the AI message
        ai_text = next(
            m.content for m in response["messages"]
            if m.__class__.__name__ == "AIMessage"
        )

        return ai_text

    # ---------------------------------------------------------
    # Helper: Formats the project data for the LLM
    # ---------------------------------------------------------
    def _format_project_json(self, project_data: Dict[str, Any]) -> str:

        project_name = project_data.get("project_name", "")
        meetings = project_data.get("meetings", [])
        user_analysis = project_data.get("user_analysis", [])

        lines = []

        # =====================================================
        # PROJECT NAME
        # =====================================================
        lines.append(f"PROJECT: {project_name}\n")

        # =====================================================
        # GLOBAL UNIQUE PARTICIPANTS
        # =====================================================
        all_participants = set()
        for m in meetings:
            all_participants.update(m.get("participants", []))

        lines.append("PARTICIPANTS:")
        for p in sorted(all_participants):
            lines.append(f"- {p}")

        # =====================================================
        # MEETING SUMMARIES
        # =====================================================
        lines.append("\nMEETINGS:")

        for idx, m in enumerate(meetings, start=1):
            meeting_name = m.get("meeting_name", "Unknown Meeting")
            meeting_time = m.get("meeting_time", "Unknown Time")

            lines.append(f"\n{idx}. {meeting_name} ({meeting_time})")
            lines.append("  summary:")

            for sp in m.get("summary_points", []):
                lines.append(f"   - {sp}")

        # =====================================================
        # PARTICIPANT INSIGHTS (cross-meeting)
        # =====================================================
        lines.append("\nPARTICIPANT INSIGHTS:")

        for entry in user_analysis:
            meeting_name = entry.get("meeting_name", "Unknown Meeting")

            for ps in entry.get("participant_summaries", []):
                name = ps.get("participant_name", "")
                lines.append(f"- {name} (from {meeting_name}):")

                # Key updates
                for ku in ps.get("key_updates", []):
                    lines.append(f"    key_update: {ku}")

                # Roadblocks
                for rb in ps.get("roadblocks", []):
                    lines.append(f"    roadblock: {rb}")

                # Actionable items
                for ac in ps.get("actionable", []):
                    lines.append(f"    actionable: {ac}")

        return "\n".join(lines)

# Example use

# # 1. Fetch project data using your tool
# project_json = fetch_project_data_from_mongo.invoke({"project_key": some_key})
#
# # 2. Generate global project summary
# global_summary_agent = GlobalProjectSummaryAgent(model, tools=[])
# output = global_summary_agent.generate_project_summary(project_json)
#
# print(output)