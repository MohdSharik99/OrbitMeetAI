import os
import asyncio
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import certifi

from langchain_groq import ChatGroq

from src.Agentic.agents.Orchestrator import build_orchestrator_graph, OrchestratorState
from src.Agentic.agents.MeetingSummaryAgent import MeetingSummaryAnalyst
from src.Agentic.agents.ParticipantAnalystAgent import ParticipantSummaryAnalyst
from src.Agentic.agents.ProjectSummaryAgent import ProjectSummaryAnalyst

from src.Agentic.utils import (
    save_summaries_to_mongo,
    fetch_project_data_from_mongo,
    save_project_summary_to_mongo,
    send_project_emails,
)


load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
mongo_uri = os.getenv("MONGO_URI")

client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
db = client["OMNI_MEET_DB"]
collection = db["Raw_Transcripts"]

DOC_ID = "6935c818994314ea5158fbb7"   # your real document id


llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2,
    api_key=api_key,
)

workflow = build_orchestrator_graph(
    MeetingSummaryAnalyst(model=llm, tools=[]),
    ParticipantSummaryAnalyst(model=llm, tools=[]),
    ProjectSummaryAnalyst(model=llm, tools=[]),
    save_summaries_to_mongo,
    fetch_project_data_from_mongo,
    save_project_summary_to_mongo,
    send_project_emails,
)


async def run_all():

    # ALWAYS fetch latest
    doc = collection.find_one({"_id": ObjectId(DOC_ID)})

    for meeting in doc["meetings"]:

        name = meeting["meeting_name"]
        already = meeting.get("processed", False)

        print()
        print("------------------------------------------------")
        print("Processing:", name, "processed=", already)

        if already:
            print("Skipping already processed.")
            continue

        transcript = meeting["Transcript"][0]

        participant_db_path = os.path.join(
            os.path.dirname(__file__),
            "SampleData",
            "participants_database.csv",
        )

        state = OrchestratorState(
            transcript=transcript,
            project_key=doc["Project_key"],
            project_name=doc["Project_name"],
            meeting_name=name,
            participants=meeting["participants"],
            participant_db_path=participant_db_path,
        )

        result = await workflow.ainvoke(state)
        print("Done running orchestrator.")

        # update flag
        upd = collection.update_one(
            {"_id": doc["_id"], "meetings.meeting_name": name},
            {"$set": {"meetings.$.processed": True}}
        )
        print("Mongo modified:", upd.modified_count)

        # VERY IMPORTANT: re-fetch so next loop sees updates
        doc = collection.find_one({"_id": ObjectId(DOC_ID)})


    print("\n========== FINAL DB CHECK ==========")
    latest = collection.find_one({"_id": ObjectId(DOC_ID)})
    for m in latest["meetings"]:
        print(m["meeting_name"], "processed=", m.get("processed", False))


if __name__ == "__main__":
    asyncio.run(run_all())
