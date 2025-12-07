"""
Background scheduler for processing new transcripts automatically.
Checks for unprocessed meetings every hour and runs the orchestrator.
"""
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

# Import orchestrator components
from src.Agentic.agents.Orchestrator import build_orchestrator_graph, OrchestratorState
from src.Agentic.agents.MeetingSummaryAgent import MeetingSummaryAnalyst
from src.Agentic.agents.ParticipantAnalystAgent import ParticipantSummaryAnalyst
from src.Agentic.agents.ProjectSummaryAgent import ProjectSummaryAnalyst
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# ======================================================================
# LOGGER CONFIGURATION
# ======================================================================
logger.remove()  # remove default
logger.add(
    sink=lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level}</level> | "
           "<cyan>{message}</cyan>"
)

# ======================================================================
# GLOBAL STATE
# ======================================================================
scheduler: Optional[AsyncIOScheduler] = None
workflow = None
agents = {}
mongo_uri = os.getenv("MONGO_URI")
participant_db_path = os.getenv("PARTICIPANT_DB_PATH", "SampleData/participants_database.csv")


# ======================================================================
# INITIALIZE ORCHESTRATOR
# ======================================================================
def initialize_orchestrator():
    """Initialize agents and workflow for processing"""
    global workflow, agents
    
    logger.info("Initializing orchestrator for scheduler...")
    
    # Load API keys
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    # Initialize LLM
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.2,
        api_key=api_key
    )
    
    # Initialize agents
    agents["summary_agent"] = MeetingSummaryAnalyst(model=llm, tools=[])
    agents["participant_agent"] = ParticipantSummaryAnalyst(model=llm, tools=[])
    agents["global_agent"] = ProjectSummaryAnalyst(model=llm, tools=[])
    
    # Import tools
    from src.Agentic.utils import save_summaries_to_mongo, fetch_project_data_from_mongo, send_project_emails, save_project_summary_to_mongo
    
    # Build orchestrator workflow
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


# ======================================================================
# FIND UNPROCESSED MEETINGS
# ======================================================================
def find_unprocessed_meetings() -> List[Dict[str, Any]]:
    """
    Find all unprocessed meetings from Raw_Transcripts collection.
    
    Returns list of dictionaries with:
    - document_id: MongoDB _id of the document
    - meeting_index: Index of the meeting in the meetings array
    - meeting_data: The meeting object
    - project_key: Project key
    - project_name: Project name
    """
    if not mongo_uri:
        logger.error("MONGO_URI not configured")
        return []
    
    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Find all documents
        documents = list(collection.find({}))
        
        unprocessed_meetings = []
        
        for doc in documents:
            document_id = doc.get("_id")
            project_key = doc.get("Project_key", "")
            project_name = doc.get("Project_name", "")
            meetings = doc.get("meetings", [])
            
            # Check each meeting in the array
            for idx, meeting in enumerate(meetings):
                # Check if processed field exists and is False, or doesn't exist
                processed = meeting.get("processed", False)
                
                if not processed:
                    unprocessed_meetings.append({
                        "document_id": document_id,
                        "meeting_index": idx,
                        "meeting_data": meeting,
                        "project_key": project_key,
                        "project_name": project_name
                    })
        
        logger.info(f"Found {len(unprocessed_meetings)} unprocessed meeting(s)")
        return unprocessed_meetings
    
    except Exception as e:
        logger.error(f"Error finding unprocessed meetings: {e}")
        return []


# ======================================================================
# MARK MEETING AS PROCESSED
# ======================================================================
def mark_meeting_as_processed(document_id: ObjectId, meeting_index: int):
    """
    Mark a meeting as processed in MongoDB.
    
    Args:
        document_id: MongoDB _id of the document
        meeting_index: Index of the meeting in the meetings array
    """
    if not mongo_uri:
        logger.error("MONGO_URI not configured")
        return
    
    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Update the specific meeting's processed field
        collection.update_one(
            {"_id": document_id},
            {"$set": {f"meetings.{meeting_index}.processed": True}}
        )
        
        logger.success(f"Marked meeting at index {meeting_index} as processed for document {document_id}")
    
    except Exception as e:
        logger.error(f"Error marking meeting as processed: {e}")


# ======================================================================
# PROCESS A SINGLE MEETING
# ======================================================================
async def process_meeting(meeting_info: Dict[str, Any]) -> bool:
    """
    Process a single meeting through the orchestrator workflow.
    
    Args:
        meeting_info: Dictionary containing meeting information from find_unprocessed_meetings()
    
    Returns:
        True if processing was successful, False otherwise
    """
    if workflow is None:
        logger.error("Workflow not initialized")
        return False
    
    document_id = meeting_info["document_id"]
    meeting_index = meeting_info["meeting_index"]
    meeting = meeting_info["meeting_data"]
    project_key = meeting_info["project_key"]
    project_name = meeting_info["project_name"]
    
    try:
        logger.info(f"Processing meeting: {meeting.get('meeting_name', 'Unknown')} "
                   f"(Document: {document_id}, Index: {meeting_index})")
        
        # Extract transcript text
        transcript_text = ""
        if "Transcript" in meeting and meeting["Transcript"]:
            if isinstance(meeting["Transcript"], list):
                transcript_text = meeting["Transcript"][0] if meeting["Transcript"] else ""
            else:
                transcript_text = str(meeting["Transcript"])
        
        if not transcript_text:
            logger.warning(f"No transcript text found for meeting at index {meeting_index}")
            return False
        
        # Create initial state
        initial_state = OrchestratorState(
            transcript=transcript_text,
            project_key=project_key,
            project_name=project_name,
            meeting_name=meeting.get("meeting_name", ""),
            participants=meeting.get("participants", []),
            participant_db_path=participant_db_path
        )
        
        # Run orchestrator workflow
        logger.info(f"Running orchestrator workflow for meeting: {meeting.get('meeting_name')}")
        final_state = await workflow.ainvoke(initial_state)
        
        # Mark as processed only if workflow completed successfully
        mark_meeting_as_processed(document_id, meeting_index)
        
        logger.success(f"Successfully processed meeting: {meeting.get('meeting_name')}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing meeting at index {meeting_index} (Document: {document_id}): {e}")
        return False


# ======================================================================
# SCHEDULED JOB: PROCESS ALL UNPROCESSED MEETINGS
# ======================================================================
async def process_unprocessed_meetings():
    """
    Scheduled job that runs every hour to process all unprocessed meetings.
    
    This function will process ALL unprocessed meetings it finds, regardless of
    when they were added. This means if the system was offline, it will catch up
    on missed meetings when it comes back online.
    """
    logger.info("=" * 60)
    logger.info(f"Scheduled job started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Find unprocessed meetings
    unprocessed = find_unprocessed_meetings()
    
    if not unprocessed:
        logger.info("No unprocessed meetings found. Skipping.")
        return
    
    logger.info(f"Processing {len(unprocessed)} unprocessed meeting(s)...")
    logger.info("Note: This includes any meetings that were missed while the system was offline.")
    
    # Process each meeting
    success_count = 0
    failure_count = 0
    
    for meeting_info in unprocessed:
        success = await process_meeting(meeting_info)
        if success:
            success_count += 1
        else:
            failure_count += 1
    
    logger.info("=" * 60)
    logger.info(f"Job completed: {success_count} succeeded, {failure_count} failed")
    logger.info("=" * 60)


# ======================================================================
# SCHEDULER SETUP
# ======================================================================
def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler is already running")
        return
    
    logger.info("Starting background scheduler...")
    
    # Initialize orchestrator
    initialize_orchestrator()
    
    # Create scheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule job to run every hour
    scheduler.add_job(
        process_unprocessed_meetings,
        trigger=CronTrigger(minute=0),  # Run at the start of every hour
        id="process_meetings",
        name="Process unprocessed meetings",
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.success("Background scheduler started. Will check for new transcripts every hour.")
    logger.info("IMPORTANT: Scheduler runs in-process. If the system goes offline, it will catch up")
    logger.info("on all unprocessed meetings when it comes back online (on the next hourly check).")


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is None:
        return
    
    logger.info("Stopping background scheduler...")
    scheduler.shutdown()
    scheduler = None
    logger.success("Background scheduler stopped")


# ======================================================================
# MANUAL TRIGGER (for testing)
# ======================================================================
async def run_manual_check():
    """Manually trigger processing of unprocessed meetings (for testing)"""
    logger.info("Manual check triggered")
    await process_unprocessed_meetings()


if __name__ == "__main__":
    # For standalone execution
    logger.info("Starting scheduler as standalone service...")
    start_scheduler()
    
    try:
        # Keep the script running
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_scheduler()

