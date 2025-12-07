"""
Scheduler for automatically uploading new transcripts from SampleData/Transcripts to MongoDB.
Runs every hour to check for new transcript files and upload them to OrbitMeetDB.raw_transcripts.
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Set, List
from pymongo import MongoClient
import certifi
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from dotenv import load_dotenv

# Import helper functions
from src.Agentic.utils.store_to_mongodb import add_transcript_to_mongo, extract_transcripts, process_transcript

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
scheduler: AsyncIOScheduler = None
mongo_uri = os.getenv("MONGO_URI")
transcripts_dir = Path("SampleData/Transcripts")
processed_files: Set[str] = set()  # Track processed files by their absolute path

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf"}


# ======================================================================
# LOAD PROCESSED FILES FROM MONGODB
# ======================================================================
def load_processed_files_from_db() -> Set[str]:
    """
    Load list of already processed files from MongoDB by checking existing project_keys.
    This helps avoid re-processing files that were already uploaded.
    
    Returns:
        Set of file paths that have been processed
    """
    if not mongo_uri:
        logger.warning("MONGO_URI not configured. Cannot load processed files from DB.")
        return set()
    
    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Get all existing project keys
        existing_projects = list(collection.find({}, {"Project_key": 1, "meetings.meeting_name": 1}))
        
        # We can't directly map files to project_keys, so we'll track by file name
        # This is a simple approach - in production you might want to store file metadata
        processed = set()
        
        logger.info(f"Loaded {len(existing_projects)} existing projects from database")
        return processed
    
    except Exception as e:
        logger.error(f"Error loading processed files from DB: {e}")
        return set()


# ======================================================================
# CHECK IF PROJECT KEY EXISTS IN MONGODB
# ======================================================================
def project_key_exists(project_key: str) -> bool:
    """
    Check if a project_key already exists in MongoDB.
    
    Args:
        project_key: The project key to check
        
    Returns:
        True if project_key exists, False otherwise
    """
    if not mongo_uri:
        logger.warning("MONGO_URI not configured. Cannot check project key.")
        return False
    
    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Check for exact match first
        existing = collection.find_one({"Project_key": project_key})
        if existing:
            return True
        
        # Also check for fuzzy matches (similar to add_transcript_to_mongo logic)
        from rapidfuzz import fuzz
        all_projects = list(collection.find({}, {"Project_key": 1}))
        
        for project in all_projects:
            existing_key = project.get("Project_key", "")
            score = fuzz.ratio(project_key.lower(), existing_key.lower())
            if score >= 90:  # 90% similarity threshold
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking project key existence: {e}")
        return False


# ======================================================================
# GET PROJECT KEY FROM TRANSCRIPT FILE
# ======================================================================
def get_project_key_from_file(file_path: Path) -> str:
    """
    Extract project key from a transcript file without uploading it.
    
    Args:
        file_path: Path to the transcript file
        
    Returns:
        Project key string, or None if extraction fails
    """
    try:
        # Use helper function to extract transcript
        transcript = extract_transcripts([str(file_path)])
        
        # Process transcript to get metadata
        meta = process_transcript(transcript)
        
        return meta.get("Project_key", "").strip()
    
    except Exception as e:
        logger.error(f"Error extracting project key from {file_path}: {e}")
        return None


# ======================================================================
# SCAN FOR NEW TRANSCRIPT FILES
# ======================================================================
def scan_for_new_transcripts() -> List[Path]:
    """
    Scan the transcripts directory for new transcript files.
    
    Returns:
        List of Path objects for new transcript files
    """
    if not transcripts_dir.exists():
        logger.warning(f"Transcripts directory does not exist: {transcripts_dir}")
        return []
    
    new_files = []
    
    # Get all supported files in the directory
    for file_path in transcripts_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            # Check if file has been processed
            abs_path = str(file_path.resolve())
            if abs_path not in processed_files:
                new_files.append(file_path)
    
    return new_files


# ======================================================================
# UPLOAD TRANSCRIPT TO MONGODB
# ======================================================================
def upload_transcript(file_path: Path) -> bool:
    """
    Upload a single transcript file to MongoDB.
    
    Args:
        file_path: Path to the transcript file
        
    Returns:
        True if upload was successful, False otherwise
    """
    abs_path = str(file_path.resolve())
    
    try:
        logger.info(f"Processing transcript file: {file_path.name}")
        
        # First, check if project_key already exists
        project_key = get_project_key_from_file(file_path)
        
        if not project_key:
            logger.warning(f"Could not extract project key from {file_path.name}. Skipping.")
            return False
        
        # Check if project_key already exists in MongoDB
        if project_key_exists(project_key):
            logger.info(f"Project key '{project_key}' already exists in database. Skipping {file_path.name}.")
            # Mark as processed even though we didn't upload (to avoid re-checking)
            processed_files.add(abs_path)
            return True
        
        # Upload transcript using the existing function
        result = add_transcript_to_mongo(str(file_path), mongo_uri)
        
        if result and "already exists" not in result.lower():
            logger.success(f"Successfully uploaded {file_path.name}: {result}")
            processed_files.add(abs_path)
            return True
        elif "already exists" in result.lower():
            logger.info(f"Transcript already exists: {file_path.name}")
            processed_files.add(abs_path)
            return True
        else:
            logger.error(f"Failed to upload {file_path.name}: {result}")
            return False
    
    except Exception as e:
        logger.error(f"Error uploading transcript {file_path.name}: {e}")
        return False


# ======================================================================
# SCHEDULED JOB: CHECK AND UPLOAD NEW TRANSCRIPTS
# ======================================================================
async def check_and_upload_transcripts():
    """
    Scheduled job that runs every hour to check for new transcripts and upload them.
    """
    logger.info("=" * 60)
    logger.info(f"Scheduled job started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Scan for new transcript files
    new_files = scan_for_new_transcripts()
    
    if not new_files:
        logger.info("No new transcript files found. Skipping.")
        return
    
    logger.info(f"Found {len(new_files)} new transcript file(s) to process...")
    
    # Upload each new file
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    for file_path in new_files:
        result = upload_transcript(file_path)
        if result:
            success_count += 1
        else:
            failure_count += 1
    
    logger.info("=" * 60)
    logger.info(f"Job completed: {success_count} succeeded, {failure_count} failed")
    logger.info("=" * 60)


# ======================================================================
# INITIALIZE PROCESSED FILES
# ======================================================================
def initialize_processed_files():
    """
    Initialize the set of processed files by scanning the directory
    and checking against MongoDB.
    """
    global processed_files
    
    logger.info("Initializing processed files tracking...")
    
    # Load from database
    db_processed = load_processed_files_from_db()
    processed_files.update(db_processed)
    
    # Also scan directory and check each file against MongoDB
    if transcripts_dir.exists():
        for file_path in transcripts_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                project_key = get_project_key_from_file(file_path)
                if project_key and project_key_exists(project_key):
                    abs_path = str(file_path.resolve())
                    processed_files.add(abs_path)
                    logger.debug(f"Marked as processed (exists in DB): {file_path.name}")
    
    logger.info(f"Initialized {len(processed_files)} processed files")


# ======================================================================
# SCHEDULER SETUP
# ======================================================================
def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler is already running")
        return
    
    logger.info("Starting transcript upload scheduler...")
    
    # Initialize processed files tracking
    initialize_processed_files()
    
    # Create scheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule job to run every hour
    scheduler.add_job(
        check_and_upload_transcripts,
        trigger=CronTrigger(minute=0),  # Run at the start of every hour
        id="upload_transcripts",
        name="Upload new transcripts to MongoDB",
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.success("Background scheduler started. Will check for new transcripts every hour.")
    logger.info(f"Monitoring directory: {transcripts_dir.absolute()}")


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is None:
        return
    
    logger.info("Stopping transcript upload scheduler...")
    scheduler.shutdown()
    scheduler = None
    logger.success("Background scheduler stopped")


# ======================================================================
# MANUAL TRIGGER (for testing)
# ======================================================================
async def run_manual_check():
    """Manually trigger check and upload of new transcripts (for testing)"""
    logger.info("Manual check triggered")
    await check_and_upload_transcripts()


# ======================================================================
# MAIN ENTRY POINT
# ======================================================================
if __name__ == "__main__":
    # For standalone execution
    logger.info("Starting transcript upload scheduler as standalone service...")
    
    # Initialize processed files
    initialize_processed_files()
    
    # Start scheduler
    start_scheduler()
    
    try:
        # Keep the script running
        # AsyncIOScheduler runs in the background, so we just need to keep the main thread alive
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_scheduler()
