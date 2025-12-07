# src/backend/scheduler.py

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import certifi

from dotenv import load_dotenv
load_dotenv()

from src.backend.db_updates import mark_meeting_processed_safe

from src.Agentic.agents.Orchestrator import build_orchestrator_graph, OrchestratorState
from src.Agentic.agents.MeetingSummaryAgent import MeetingSummaryAnalyst
from src.Agentic.agents.ParticipantAnalystAgent import ParticipantSummaryAnalyst
from src.Agentic.agents.ProjectSummaryAgent import ProjectSummaryAnalyst
from langchain_groq import ChatGroq

from src.Agentic.utils import (
    save_summaries_to_mongo,
    fetch_project_data_from_mongo,
    send_project_emails,
    save_project_summary_to_mongo
)

logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"
)

scheduler: Optional[AsyncIOScheduler] = None
workflow = None
agents = {}
mongo_uri = os.getenv("MONGO_URI")
participant_db_path = os.getenv("PARTICIPANT_DB_PATH", "SampleData/participants_database.csv")


def initialize_orchestrator():
    global workflow, agents

    logger.info("Initializing orchestrator for scheduler...")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.2,
        api_key=api_key
    )

    agents["summary_agent"] = MeetingSummaryAnalyst(model=llm, tools=[])
    agents["participant_agent"] = ParticipantSummaryAnalyst(model=llm, tools=[])
    agents["global_agent"] = ProjectSummaryAnalyst(model=llm, tools=[])

    workflow = build_orchestrator_graph(
        agents["summary_agent"],
        agents["participant_agent"],
        agents["global_agent"],
        save_summaries_to_mongo,
        fetch_project_data_from_mongo,
        save_project_summary_to_mongo,
        send_project_emails,
    )

    logger.success("Orchestrator initialized successfully")


async def process_document(document_id: ObjectId):
    """
    Process all unprocessed meetings inside a single document sequentially.
    Re-fetches document after each meeting to avoid stale state.
    """

    if not mongo_uri:
        logger.error("MONGO_URI not configured")
        return 0, 0

    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
    db = client["OMNI_MEET_DB"]
    collection = db["Raw_Transcripts"]

    success = 0
    fail = 0

    # IMPORTANT: always re-load after each update
    while True:
        doc = collection.find_one({"_id": document_id})
        if not doc:
            logger.error(f"Document not found: {document_id}")
            break

        project_key = doc.get("Project_key", "")
        project_name = doc.get("Project_name", "")

        found_unprocessed = False

        for m in doc.get("meetings", []):
            if m.get("processed", False):
                continue

            found_unprocessed = True

            meeting_name = m.get("meeting_name","")
            logger.info(f"Processing meeting: {meeting_name}")

            transcript = ""
            t_val = m.get("Transcript")
            if isinstance(t_val, list):
                transcript = t_val[0] if t_val else ""
            else:
                transcript = t_val

            if not transcript:
                logger.warning("No transcript text, skipping")
                fail += 1
                continue

            initial_state = OrchestratorState(
                transcript=transcript,
                project_key=project_key,
                project_name=project_name,
                meeting_name=meeting_name,
                participants=m.get("participants", []),
                participant_db_path=participant_db_path,
            )

            try:
                await workflow.ainvoke(initial_state)

                updated = mark_meeting_processed_safe(str(document_id), meeting_name)
                if updated:
                    logger.success(f"Processed meeting: {meeting_name}")
                    success += 1
                else:
                    logger.error(f"Failed updating flag: {meeting_name}")
                    fail += 1

            except Exception as e:
                logger.error(f"Error in meeting {meeting_name}: {e}")
                fail += 1

            break  # after processing one, re-fetch document via while

        if not found_unprocessed:
            break

    return success, fail


async def process_unprocessed_meetings():
    logger.info("="*60)
    logger.info(f"Scheduled at {datetime.now()}")
    logger.info("="*60)

    if workflow is None:
        logger.error("Workflow not initialized")
        return

    if not mongo_uri:
        logger.error("MONGO_URI not configured")
        return

    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
    db = client["OMNI_MEET_DB"]
    collection = db["Raw_Transcripts"]

    documents = list(collection.find({}))

    total_success = 0
    total_fail = 0

    for doc in documents:
        s, f = await process_document(doc["_id"])
        total_success += s
        total_fail += f

    logger.info(f"Scheduler done: success={total_success}, fail={total_fail}")


def start_scheduler():
    global scheduler

    if scheduler:
        logger.warning("Scheduler already running")
        return

    initialize_orchestrator()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(process_unprocessed_meetings, CronTrigger(minute=0))
    scheduler.start()

    logger.success("Scheduler started")


def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None


async def run_manual_check():
    logger.info("Manual run")
    await process_unprocessed_meetings()


async def main():
    start_scheduler()
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
