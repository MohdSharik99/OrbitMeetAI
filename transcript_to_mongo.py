"""
Scheduler for automatically uploading new transcripts from SampleData/Transcripts to MongoDB.
Runs every hour to check for new transcript files and upload them to OMNI_MEET_DB.Raw_Transcripts.
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

# helper functions
from src.Agentic.utils.store_to_mongodb import (
    add_transcript_to_mongo,
    extract_transcripts,
    process_transcript,
)

load_dotenv()


# ======================================================================
# LOGGER CONFIG
# ======================================================================
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"
)


# ======================================================================
# GLOBAL
# ======================================================================
scheduler: AsyncIOScheduler = None
mongo_uri = os.getenv("MONGO_URI")
transcripts_dir = Path("SampleData/Transcripts")
processed_files: Set[str] = set()

SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf"}


# ======================================================================
# LOAD processed filenames from DB
# ======================================================================
def load_processed_files_from_db() -> Set[str]:
    processed = set()
    if not mongo_uri:
        return processed

    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]

        for doc in collection.find({}, {"source_files": 1}):
            for fname in doc.get("source_files", []):
                processed.add(fname)

        logger.info(f"Loaded {len(processed)} processed filenames from DB")
        return processed

    except Exception as e:
        logger.error(f"Error loading processed files: {e}")
        return processed


# ======================================================================
# EXTRACT project key from a transcript
# ======================================================================
def get_project_key_from_file(file_path: Path) -> str:
    try:
        transcript = extract_transcripts([str(file_path)])
        meta = process_transcript(transcript)
        return meta.get("Project_key", "").strip()

    except Exception as e:
        logger.error(f"Error extracting project key from {file_path}: {e}")
        return None


# ======================================================================
# Scan for new transcription files
# ======================================================================
def scan_for_new_transcripts() -> List[Path]:
    if not transcripts_dir.exists():
        logger.warning(f"Transcripts directory does not exist: {transcripts_dir}")
        return []

    new_files = []
    for file_path in transcripts_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            if file_path.name not in processed_files:
                new_files.append(file_path)

    return new_files


# ======================================================================
# Upload a transcript (append if project exists)
# ======================================================================
def upload_transcript(file_path: Path) -> bool:
    filename = file_path.name

    try:
        logger.info(f"Processing transcript file: {filename}")

        project_key = get_project_key_from_file(file_path)
        if not project_key:
            logger.warning(f"Cannot extract project key from {filename}")
            return False

        # always call add_transcript_to_mongo so it can append meetings
        result = add_transcript_to_mongo(str(file_path), mongo_uri)

        # mark processed regardless of append or exists
        processed_files.add(filename)

        # store filename in DB
        try:
            client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
            db = client["OMNI_MEET_DB"]
            db["Raw_Transcripts"].update_one(
                {"Project_key": project_key},
                {"$addToSet": {"source_files": filename}}
            )
        except Exception as e:
            logger.warning(f"Could not store filename in DB: {e}")

        if result and "already exists" not in result.lower():
            logger.success(f"Uploaded {filename}: {result}")
        else:
            logger.info(f"Transcript existed or appended: {filename}")

        return True

    except Exception as e:
        logger.error(f"Error uploading transcript {filename}: {e}")
        return False


# ======================================================================
# Scheduled job
# ======================================================================
async def check_and_upload_transcripts():
    logger.info("=" * 60)
    logger.info(f"Scheduled job started at {datetime.now():%Y-%m-%d %H:%M:%S}")
    logger.info("=" * 60)

    new_files = scan_for_new_transcripts()
    if not new_files:
        logger.info("No new transcript files found.")
        return

    logger.info(f"Found {len(new_files)} new file(s) to process")

    success_count = 0
    failure_count = 0

    for file_path in new_files:
        ok = upload_transcript(file_path)
        if ok:
            success_count += 1
        else:
            failure_count += 1

    logger.info(f"Completed. success={success_count}, fail={failure_count}")
    logger.info("=" * 60)


# ======================================================================
# Initialize processed files
# ======================================================================
def initialize_processed_files():
    global processed_files

    logger.info("Initializing processed files...")

    # load from DB
    processed_files.update(load_processed_files_from_db())

    logger.info(f"Loaded {len(processed_files)} processed files")


# ======================================================================
# Scheduler control
# ======================================================================
def start_scheduler():
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    logger.info("Starting transcript upload scheduler...")
    initialize_processed_files()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_upload_transcripts,
        trigger=CronTrigger(minute=0),
        id="upload_transcripts",
        replace_existing=True
    )
    scheduler.start()

    logger.success("Background transcript scheduler started.")


def stop_scheduler():
    global scheduler

    if scheduler is None:
        return

    logger.info("Stopping transcript upload scheduler...")
    scheduler.shutdown()
    scheduler = None
    logger.success("Transcript scheduler stopped")


# ======================================================================
# Manual trigger (testing)
# ======================================================================
async def run_manual_check():
    logger.info("Manual check triggered")
    await check_and_upload_transcripts()


# ======================================================================
# Entry point
# ======================================================================
if __name__ == "__main__":
    logger.info("Starting transcript upload scheduler as standalone service...")

    initialize_processed_files()

    async def main():
        start_scheduler()
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        stop_scheduler()
