from src.agents.TaskActionableAgent import UserAnalysisAgent
from src.agents.SummarizerAgent import SummaryAgent
from src.utils.tools import orbit_meet_tool, format_normalize_tool
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain.messages import AIMessage, HumanMessage
import os


transcript = """
[00:00:02] John Doe
Hi everyone, thanks for joining today's sync. We'll go over the project updates and blockers.

[00:00:10] Sarah Smith
Thanks John. I’ll start with my update. The API integration for the payment service is about 80% complete.
I expect to finish the remaining tasks by Thursday.

[00:00:25] John Doe
Great. Any blockers?

[00:00:27] Sarah Smith
Yes, I’m waiting for access to the staging environment. I've already raised a ticket but haven't received approval yet.

[00:00:40] Michael Lee
I can help with that. I’ll follow up with DevOps and get the access approved today.

[00:00:48] John Doe
Perfect. Michael, your updates?

[00:00:50] Michael Lee
Sure. The UI redesign for the dashboard is complete. I’ve pushed it to the feature branch.
Only pending item is final QA review scheduled for tomorrow.

[00:01:05] John Doe
Good progress. Before we wrap up, any announcements or concerns?

[00:01:12] Sarah Smith
None from my side.

[00:01:14] Michael Lee
All good here.

[00:01:17] John Doe
Alright, thanks everyone. We'll meet again next Monday. Have a great day!
"""


# --------------------------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.7,
    api_key=api_key
)

# --------------------------------------------------------------------------------------------
# User Analysis Agent
# --------------------------------------------------------------------------------------------

# my_agent = UserAnalysisAgent(model=llm, tools= [])
#
# json_result = my_agent.participant_analysis(input_transcript=transcript)
#
# user_schema = my_agent.parse_output_to_schema(text=json_result)
#
# # print(json_result)
#
#
# p_list = []
# for r in user_schema:
#     p_list.append({
#         "participant_name": r.participant_summary.participant_name,
#         "roadblocks": r.participant_summary.roadblocks
#     })
#
# print(p_list)




# --------------------------------------------------------------------------------------------
# Summary analysis
# --------------------------------------------------------------------------------------------

# Usage
my_agent = SummaryAgent(model=llm, tools=[])

# Get validated Pydantic object
summary = my_agent.generate_summary(input_transcript=transcript)

# This will display as a Pydantic object
print(summary)



