import os
from langchain.tools import tool
from typing import Dict, Any, Optional, List
import pdfplumber
from docx import Document
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import smtplib
import uuid
from dotenv import load_dotenv
from pymongo import MongoClient
from src.utils.pydantic_schemas import MeetingMetadata, MeetingAnalysis

# -----------------------------
# File processors with inline normalization
# -----------------------------
def _process_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return "\n".join(line.strip() for line in f.read().replace("\r", "").split("\n") if line.strip())

def _process_docx(file_path):
    doc = Document(file_path)
    return "\n".join(line.strip() for p in doc.paragraphs for line in p.text.replace("\r", "").split("\n") if line.strip())

def _process_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return "\n".join(line.strip() for line in text.replace("\r", "").split("\n") if line.strip())

def _process_srt(file_path):
    lines = open(file_path, "r", encoding="utf-8").read().split("\n")
    text_lines = [
        line.strip() for line in lines
        if line.strip() and "-->" not in line and not line.strip().isdigit()
    ]
    return "\n".join(text_lines)

def _process_vtt(file_path):
    lines = open(file_path, "r", encoding="utf-8").read().split("\n")
    text_lines = [
        line.strip() for line in lines
        if line.strip() and "-->" not in line and not line.startswith("WEBVTT")
    ]
    return "\n".join(text_lines)

# Dispatcher
PROCESSORS = {
    ".txt": _process_txt,
    ".docx": _process_docx,
    ".pdf": _process_pdf,
    ".srt": _process_srt,
    ".vtt": _process_vtt,
}

def process_file(file_path: str) -> str:
    """Detect file type and process using the corresponding processor."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in PROCESSORS:
        raise ValueError(f"Unsupported file type: {ext}")

    return PROCESSORS[ext](file_path)

# -----------------------------
# LangChain Tool
# -----------------------------
@tool
def format_normalize_tool(file_path: str) -> str:
    """
    Detect transcript file format and convert to standardized text format.

    Args:
        file_path: Path to the transcript file

    Returns:
        str: Normalized text content in consistent format
    """
    try:
        return process_file(file_path)
    except Exception as e:
        return f"Error processing file: {str(e)}"


################################### META DATA EXTRACTION TOOL ##############################################3


@tool
def metadata_tool(transcript: str) -> str:
    """
    Extract structured meeting metadata from transcript.
    Returns JSON string that can be parsed into MeetingMetadata.
    The agent's LLM will perform the actual analysis when calling this tool.
    """
    from langchain_core.output_parsers import PydanticOutputParser

    parser = PydanticOutputParser(pydantic_object=MeetingMetadata)

    special_instructions = """
SPECIAL PARSING INSTRUCTIONS:
- meeting_time: Extract from timestamp patterns like 20251130_093000 → 30 November 2025, 09:30am
- project_name: Extract from meeting titles before timestamps, avoid part1, followup etc.
- meeting_name: Same as project_name but can be a followup, part1, part2, etc.
- duration: Extract from the next line of meeting_time like 51m 18s, 30m 15s 
- participants: Extract names from speaker lines and infer roles from context

Example: "Project Phoenix -Part 1-20251130_093000-Meeting Recording" should parse as:
- project_name: "Project Phoenix"
- meeting_name: "Project Phoenix - Part 1
- meeting_time: "30 November 2025, 09:30am"
- meeting_name: "Meeting Recording"
"""

    return f"{special_instructions}\n\nReturn in this format: {parser.get_format_instructions()}"



###################################### ORBIT MEET FORMAT TOOL ####################################

from langchain.tools import tool
from langchain_core.messages import SystemMessage

# Define the system prompt with all instructions and examples
SYSTEM_PROMPT = """Convert any transcript to ORBIT MEET (Same as MS Teams) format if not already formatted:

FIRST: If already in MS Teams format (**Title**, **Speaker** MM:SS), return as-is.

TARGET FORMAT:
**Title**
Date & Time
Duration  
Transcription Starter

**Speaker** MM:SS
Message
[empty line between speakers]

CONVERSION RULES:
- If already in MS Teams format, return as-is
- Timestamps: [HH:MM:SS] → MM:SS, HH:MM:SS AM/PM → MM:SS, SPEAKER_01 (HH:MM:SS) → MM:SS
- Speakers: SPEAKER_01 → Speaker 1, John D. → John, merge multi-line text
- Metadata: Extract from headers or use defaults
- Defaults: "Meeting Transcript", "Date not specified", "Duration not specified", "System started transcription"
- No timestamps? Start at 0:04, increment by 10s

EXPECTED OUTPUT EXAMPLES:

Example 1:
**Project Nexus Launch Retrospective & Q2 Planning-20251203_150000-Meeting Recording**
03 December 2025, 03:00pm
51m 18s
CHEN, Lisa started transcription

**Lisa Chen** 0:03
Okay, I think we're all here. Good afternoon everyone. Let's begin. As you know, Project Nexus officially launched last Tuesday, and today we're here to do a thorough retrospective and start looking ahead to Q2. I want this to be an honest, constructive conversation.

**Ben Carter** 0:20
Afternoon, Lisa. Team.



Example 2:
**Project Phoenix - Sprint 15 Planning & Tech Deep Dive-20251130_093000-Meeting Recording**
30 November 2025, 09:30am
31m 15s
PATEL, Priya started transcription

**Priya Patel** 0:02
Okay, I think everyone's here. Good morning, team. Let's get started. Thanks for making it. The agenda for today is sprint 15 planning, a deep dive on the new user authentication migration, and then open floor for any blockers.

**Ben Carter** 0:15
Morning, Priya. Everyone. Ready to go.



INPUT EXAMPLES (Different formats you might receive):

Input (Zoom): [00:00:05] Alice: Hello
Input (Webex): 10:05:15 AM John: Message  
Input (Speaker Diarization): SPEAKER_00 (00:00:05): Let's begin
Input (Already formatted): **Meeting**\nDate\nDuration\nStarter\n\n**John** 0:05\nMessage

All should convert to the TARGET FORMAT shown above.

Now convert this transcript:

{transcript}

Output:"""


# LangChain tool version
@tool
def orbit_meet_tool(transcript_text: str) -> str:
    """
    Convert various transcript formats to consistent MS Teams-compatible format.

    Args:
        transcript_text: Raw transcript text in various formats

    Returns:
        str: Formatted transcript in consistent MS Teams format
    """
    # This would be implemented with your actual LLM call
    # For now, return the formatted prompt
    return SYSTEM_PROMPT.format(transcript=transcript_text)


# -------------------------------------------------------------------------------------------------
# send_email_tool
# -------------------------------------------------------------------------------------------------

# Gmail SMTP settings



@tool
def send_email_tool(to_email: List[str], subject: List[str], body: List[str]) -> str:
    """
    Send an email using fixed Gmail SMTP credentials.

    Args:
        to_email: Recipient email.
        subject: Subject line.
        body: Email body (HTML allowed).

    Returns:
        str: Status message.
    """
    load_dotenv()
    SENDER_EMAIL= os.getenv("SENDER_EMAIL")
    SMTP_SERVER= os.getenv("SMTP_SERVER")
    SMTP_PORT= os.getenv("SMTP_PORT")
    SENDER_PASSWORD=os.getenv("SENDER_PASSWORD")



    # Create Email
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    # SSL encrypted connection (Gmail requirement)
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

    return f"Email sent successfully to {to_email}"




# ----------------------------------------------------------------------------------------------
# Save to MongoDB
# ----------------------------------------------------------------------------------------------

@tool
def save_meeting_analysis_to_mongo(data: Dict[str, Any]) -> str:
    """
    Saves meeting metadata, summary, and user analysis to MongoDB Atlas.
    Updates project documents if project_id exists.
    Returns project name and meeting name instead of IDs.
    """
    mongo_uri = os.getenv("MONGO_URI")  # Mongo URI from .env
    client = MongoClient(mongo_uri)
    db = client["meeting_db"]
    summary_collection = db["meeting_summary"]
    user_analysis_collection = db["useranalysis"]

    # Validate input
    meeting_analysis = MeetingAnalysis(**data)
    metadata = meeting_analysis.metadata
    summary = meeting_analysis.summary
    user_analysis = meeting_analysis.user_analysis

    if not metadata.project_id:
        return "Project ID is None. Meeting not saved."

    # ----------------------
    # Update or insert meeting_summary
    # ----------------------
    summary_doc = {
        "meeting_id": metadata.meeting_id,
        "meeting_name": metadata.meeting_name,
        "meeting_time": metadata.meeting_time,
        "duration": metadata.duration,
        "participants": [p.dict() for p in metadata.participants],
        "summary_points": summary.summary_points
    }

    summary_collection.update_one(
        {"project_id": metadata.project_id},
        {"$push": {"meetings": summary_doc}},
        upsert=True
    )

    # ----------------------
    # Update or insert useranalysis
    # ----------------------
    user_docs = []
    for ua in user_analysis:
        user_docs.append({
            "meeting_id": metadata.meeting_id,
            "participant_summary": ua.participant_summary.dict()
        })

    user_analysis_collection.update_one(
        {"project_id": metadata.project_id},
        {"$push": {"meetings": {"$each": user_docs}}},
        upsert=True
    )

    return f"Meeting '{metadata.meeting_name}' saved under project '{metadata.project_name}' in both collections."


# ----------------------------------------------------------------------------------------------------------------
# Fetch overall project history
# ----------------------------------------------------------------------------------------------------------------

@tool
def fetch_project_data_from_mongo(
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetches project meetings and user analysis data from MongoDB.
    Either project_id (UUID string) or project_name must be provided.
    Returns a combined dict with meeting summaries and user analysis.
    """
    if not project_id and not project_name:
        return {"error": "Please provide either project_id or project_name."}

    mongo_uri = os.getenv("MONGO_URI")

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client["meeting_db"]
    meeting_collection = db["meeting_summary"]
    user_collection = db["user_analysis"]

    # Build query
    query = {}
    if project_id:
        query["project_id"] = uuid.UUID(project_id)
    if project_name:
        query["metadata.project_name"] = project_name

    # Fetch meeting summaries
    project_doc = meeting_collection.find_one(query)
    if not project_doc:
        return {"error": "Project not found."}

    # Fetch user analysis for the same project
    user_docs = list(user_collection.find(query, {"_id": 0}))

    # Return combined data
    return {
        "project_name": project_doc["metadata"]["project_name"],
        "meetings": project_doc.get("meetings", []),
        "user_analysis": user_docs
    }
