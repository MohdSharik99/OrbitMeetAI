import os
from langchain.tools import tool
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
import csv
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime


load_dotenv()

#=====================================================================================================
# Save transcript summaries into MongoDB
#=====================================================================================================
@tool
def save_summaries_to_mongo(
    core_agent: str,
    project_key: str,
    project_name: str,
    meeting_name: str,
    data: Any
) -> str:
    """
    Saves SummaryList OR ParticipantAnalysis list into MongoDB.
    Prevents duplicate entries based on meeting_name.
    """

    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]

    # ====================================================================
    # 1. SAVE MEETING SUMMARY (meeting_summary collection)
    # ====================================================================
    if core_agent == "summary":

        col = db["Meeting_summary"]

        # Does meeting summary already exist?
        existing = col.find_one(
            {"project_key": project_key, "meetings.meeting_name": meeting_name},
            {"_id": 1}
        )
        if existing:
            return (
                f"Meeting summary for '{meeting_name}' already exists "
                f"in project '{project_key}'. Skipping insert."
            )

        # New document to insert into "meetings" array
        summary_doc = {
            "meeting_name": meeting_name,
            "participants": data["participants"],
            "summary_points": data["summary_points"]
        }

        col.update_one(
            {"project_key": project_key},
            {
                "$setOnInsert": {
                    "project_key": project_key,
                    "project_name": project_name
                },
                "$push": {"meetings": summary_doc}
            },
            upsert=True
        )

        return (
            f"Meeting summary saved for meeting '{meeting_name}' "
            f"in project '{project_key}'."
        )

    # ====================================================================
    # 2. SAVE PARTICIPANT SUMMARY (participants_analysis collection)
    # ====================================================================
    elif core_agent == "participant_summary":

        col = db["Participants_analysis"]

        # Does participant analysis already exist?
        existing = col.find_one(
            {"project_key": project_key, "meetings.meeting_name": meeting_name},
            {"_id": 1}
        )
        if existing:
            return (
                f"Participant analysis for '{meeting_name}' already exists "
                f"in project '{project_key}'. Skipping insert."
            )

        participant_summaries = [
            item["participant_summary"] for item in data
        ]

        meeting_entry = {
            "meeting_name": meeting_name,
            "participant_summaries": participant_summaries
        }

        col.update_one(
            {"project_key": project_key},
            {
                "$setOnInsert": {
                    "project_key": project_key,
                    "project_name": project_name
                },
                "$push": {"meetings": meeting_entry}
            },
            upsert=True
        )

        return (
            f"Participant summary saved for meeting '{meeting_name}' "
            f"in project '{project_key}'."
        )

    # ====================================================================
    # ERROR CASE
    # ====================================================================
    else:
        return "ERROR: core_agent must be 'summary' or 'participant_summary'."

# =====================================================================================================
# Save Project Summary to MongoDB
# =====================================================================================================
@tool
def save_project_summary_to_mongo(
    project_key: str,
    project_name: str,
    global_summary: str
) -> str:
    """
    Saves or updates the global project summary in Project_summary collection.
    
    This updates the project summary document with the latest global summary.
    Since the global summary is generated from all meetings, it should be updated
    each time a new meeting is processed.
    """
    
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]
    col = db["Project_summary"]
    
    # Update or insert project summary
    col.update_one(
        {"project_key": project_key},
        {
            "$set": {
                "project_key": project_key,
                "project_name": project_name,
                "global_summary": global_summary,
                "last_updated": datetime.now().isoformat()
            }
        },
        upsert=True
    )
    
    return (
        f"Project summary saved/updated for project '{project_key}'."
    )

# =====================================================================================================
# Fetch complete project history from MongoDB
# =====================================================================================================

@tool
def fetch_project_data_from_mongo(
    project_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches full project data (meeting summaries + participant analysis)
    using project_key as the identifier.
    """

    if not project_key:
        return {"error": "project_key is required."}

    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]

    meeting_collection = db["Meeting_summary"]
    user_collection = db["Participants_analysis"]

    # ----------------------------
    # Fetch meeting summaries
    # ----------------------------
    meeting_doc = meeting_collection.find_one(
        {"project_key": project_key},
        {"_id": 0}
    )

    if not meeting_doc:
        return {"error": "Project not found."}

    # ----------------------------
    # Fetch participant analysis
    # ----------------------------
    user_doc = user_collection.find_one(
        {"project_key": project_key},
        {"_id": 0}
    )

    user_meetings = user_doc.get("meetings", []) if user_doc else []

    # ----------------------------
    # Combine and return
    # ----------------------------
    return {
        "project_key": meeting_doc["project_key"],
        "project_name": meeting_doc["project_name"],
        "meetings": meeting_doc.get("meetings", []),
        "user_analysis": user_meetings
    }


# =====================================================================================================
# Email Sending Tool
# =====================================================================================================
@tool
def send_project_emails(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends emails ONLY to actual meeting participants.
    Executives get global summary section.
    Non-exec participants get meeting + participant sections.
    """

    import os, csv, ssl, smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from datetime import datetime

    # Required meeting data
    meeting_name = input_data["meeting_name"]
    project_name = input_data["project_name"]

    meeting_text = input_data["meeting_summary_text"]
    participant_text = input_data["participant_analysis_text"]
    global_text = input_data["global_summary_text"]

    # IMPORTANT: this MUST exist now
    meeting_participants = {p.lower().strip() for p in input_data.get("participants", [])}

    # Load our CSV participants
    participant_db_path = input_data.get("participant_db_path", "SampleData/participants_database.csv")
    real_people = []
    with open(participant_db_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # name match using lowercase
            if row["EmployeeName"].lower().strip() in meeting_participants:
                real_people.append({
                    "name": row["EmployeeName"],
                    "email": row["EmployeeEmail"],
                    "role": row["Role"].lower().strip()
                })

    EXEC_ROLES = {
        "manager", "senior manager", "director", "vp", "vice president",
        "chief", "head", "lead"
    }

    # Email formatting helpers
    def to_bullets(text: str) -> str:
        items = [f"<li>{l.strip()}</li>" for l in text.split("\n") if l.strip()]
        return "<ul>" + "".join(items) + "</ul>"

    def format_global_summary(global_text: str):
        if not global_text.strip():
            return ""
        return f"""
        <div><h2>Executive Summary</h2>
        <div>{global_text}</div></div>
        """

    def format_participant_summary(text: str):
        if not text.strip():
            return ""
        return f"<div><h2>Participant Highlights</h2><div>{text}</div></div>"

    meeting_html = to_bullets(meeting_text)

    # SMTP
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    context = ssl.create_default_context()
    sent = []

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)

        for p in real_people:
            is_exec = p["role"] in EXEC_ROLES

            body = meeting_html
            if is_exec:
                body += format_global_summary(global_text)
            else:
                body += format_participant_summary(participant_text)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Meeting Summary: {meeting_name}"
            msg["From"] = SMTP_EMAIL
            msg["To"] = p["email"]
            msg.attach(MIMEText(body, "html"))

            smtp.sendmail(SMTP_EMAIL, p["email"], msg.as_string())
            sent.append({"email": p["email"], "role": p["role"]})

    return {
        "status": "success",
        "meeting_name": meeting_name,
        "sent": sent
    }
