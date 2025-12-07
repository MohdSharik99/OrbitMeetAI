import os
import asyncio
from pymongo import MongoClient
from bson import ObjectId

from langchain_groq import ChatGroq
from dotenv import load_dotenv
import certifi

# Orchestrator + Tools
from src.Agentic.agents.Orchestrator import build_orchestrator_graph
from src.Agentic.utils import save_summaries_to_mongo
from src.Agentic.utils import fetch_project_data_from_mongo
from src.Agentic.utils import send_project_emails
from src.Agentic.agents.Orchestrator import OrchestratorState

# Agents
from src.Agentic.agents.MeetingSummaryAgent import MeetingSummaryAnalyst
from src.Agentic.agents.ParticipantAnalystAgent import ParticipantSummaryAnalyst
from src.Agentic.agents.ProjectSummaryAgent import ProjectSummaryAnalyst


# -----------------------------------
# Load environment variables
# -----------------------------------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
mongo_uri = os.getenv("MONGO_URI")




# -----------------------------------
# Initialize LLM
# -----------------------------------
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2,
    api_key=api_key
)


# -----------------------------------
# Build Orchestrator Graph
# -----------------------------------
summary_agent = MeetingSummaryAnalyst(model=llm, tools=[])
participant_agent = ParticipantSummaryAnalyst(model=llm, tools=[])
global_agent = ProjectSummaryAnalyst(model=llm, tools=[])

workflow = build_orchestrator_graph(
    summary_agent,
    participant_agent,
    global_agent,
    save_summaries_to_mongo,
    fetch_project_data_from_mongo,
    send_project_emails,
)


# -----------------------------------
# Fetch transcript from Mongo
# -----------------------------------
client = MongoClient(mongo_uri,
                     tls=True,
                     tlsCAFile=certifi.where())

db = client["OMNI_MEET_DB"]
collection = db["Raw_Transcripts"]

doc = collection.find_one({"_id": ObjectId("6934ad0253aab1b5579695e2")})

if not doc:
    raise ValueError("No transcript found for that ID")

meeting = doc["meetings"][0]

initial_state = OrchestratorState(
    transcript=meeting["Transcript"][0],
    project_key=doc["Project_key"],
    project_name=doc["Project_name"],
    meeting_name=meeting["meeting_name"],
    participants=meeting["participants"],
    participant_db_path=r"C:\Users\mohds\PycharmProjects\OrbitMeetAI\SampleData\participants_database.csv"
)



# -----------------------------------
# Run the orchestrator async
# -----------------------------------
final_state = asyncio.run(workflow.ainvoke(initial_state))


# -----------------------------------
# Output results
# -----------------------------------
print("============ GLOBAL SUMMARY ============")
print(final_state["global_summary"])




print("\n============ PROJECT DATA ============")
print(final_state["project_data"])

print("\n============ EMAILS SENT SUCCESSFULLY ============")
