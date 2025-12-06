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
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

#=====================================================================================================
# Save transcript into MongoDB
#=====================================================================================================


@tool
def save_summaries_to_mongo(
    core_agent: str,
    project_key: str,
    project_id: Optional[str],
    project_name: str,
    meeting_name: str,
    data: Any
) -> str:
    """
    Saves SummaryList OR ParticipantAnalysis list to MongoDB depending on core_agent value.

    core_agent options:
      - "summary"              → save SummaryList fields into meeting_summary collection
      - "participant_summary"  → save UsersAnalysis list into participants_analysis collection

    Arguments:
        core_agent: Which output we are saving ("summary" or "participant_summary")
        project_key: Unique project key string
        project_id: Deterministic project id
        project_name: Full project name
        meeting_name: Name of the meeting
        data:
            If core_agent="summary": expects SummaryList.model_dump()
            If core_agent="participant_summary": expects [UsersAnalysis.model_dump(), ...]

    Returns:
        str: Success message
    """

    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]


    # CASE 1: SAVE MEETING SUMMARY
    if core_agent == "summary":

        col = db["meeting_summary"]

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
                    "project_id": project_id,
                    "project_name": project_name
                },
                "$push": {
                    "meetings": summary_doc
                }
            },
            upsert=True
        )

        return f"Meeting summary saved for meeting '{meeting_name}' in project '{project_key}'."


    # CASE 2: SAVE PARTICIPANT SUMMARY
    elif core_agent == "participant_summary":

        col = db["participants_analysis"]

        # Extract only participant_summary objects from the list
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
                    "project_id": project_id,
                    "project_name": project_name
                },
                "$push": {
                    "meetings": meeting_entry
                }
            },
            upsert=True
        )

        return f"Participant summary saved for meeting '{meeting_name}' in project '{project_key}'."

    # ERROR CASE
    else:
        return "ERROR: core_agent must be 'summary' or 'participant_summary'."


# ----------------------------------------------------------------------------------------------------------------
# Fetch overall project history
# ----------------------------------------------------------------------------------------------------------------

@tool
def fetch_project_data_from_mongo(
    project_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches full project data (meeting summaries + participant analysis)
    using project_key as the identifier.
    Expected Input Format:

    {
        "project_key": str,
        "project_id": str,
        "project_name": str,

        "meetings": [
            {
                "meeting_name": str,
                "meeting_time": str,
                "participants": [str, ...],
                "summary_points": [str, ...]
            },
            ...
        ],

        "user_analysis": [
            {
                "meeting_name": str,
                "participant_summaries": [
                    {
                        "participant_name": str,
                        "key_updates": [str, ...],
                        "roadblocks": [str, ...],
                        "actionable": [str, ...]
                    },
                    ...
                ]
            },
            ...
        ]
    }

    """

    if not project_key:
        return {"error": "project_key is required."}

    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]   # fixed DB name

    meeting_collection = db["meeting_summary"]
    user_collection = db["participants_analysis"]

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
        "project_id": meeting_doc["project_id"],
        "project_name": meeting_doc["project_name"],
        "meetings": meeting_doc.get("meetings", []),
        "user_analysis": user_meetings
    }

# -----------------------------------------------------------------------
# Email Tool- Sharik
# ----------------------------------------------------------------------------------

@tool
def send_project_emails(
    input_data: Dict[str, Any],
    participant_db_path: str = "participants_data.csv",
) -> Dict[str, Any]:
    """
    Sends meeting-related emails based on roles.

    Args:
        input_data: {
            "project_key": "...",
            "meeting_summary_text": "...",
            "participant_analysis_text": "...",
            "global_summary_text": "..."
        }

        participant_db_path: path to participants CSV (default: participants_data.csv)
    """

    project_key = input_data["project_key"]
    meeting_text = input_data["meeting_summary_text"]
    participant_text = input_data["participant_analysis_text"]
    global_text = input_data["global_summary_text"]

    # Convert plain text → HTML
    def to_html(text: str) -> str:
        return "<div style='font-family:Arial;font-size:14px;'>" + text.replace("\n", "<br>") + "</div>"

    meeting_html = to_html(meeting_text)
    participant_html = to_html(participant_text)
    global_html = to_html(global_text)

    # ------------------------------------------------------
    # LOAD PARTICIPANT DATABASE (using argument)
    # ------------------------------------------------------
    participants = []
    with open(participant_db_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            participants.append({
                "name": row["name"],
                "email": row["email"],
                "role": row["role"].lower().strip(),
                "department": row["department"]
            })

    # ------------------------------------------------------
    # SMTP
    # ------------------------------------------------------
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    smtp.starttls()
    smtp.login(SMTP_USER, SMTP_PASSWORD)

    # Email sending helper
    def send(email_to: str, subject: str, html: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = email_to
        msg.attach(MIMEText(html, "html"))
        smtp.sendmail(SMTP_USER, email_to, msg.as_string())

    EXECUTIVE_ROLES = ["manager", "senior manager", "director", "vp", "vice president", "chief", "head", "lead"]

    combined_html = f"""
    <html><body>
        <h2>Meeting Summary</h2>
        {meeting_html}
        <hr>
        <h2>Participant Analysis</h2>
        {participant_html}
    </body></html>
    """

    sent = {"participants": [], "executives": []}

    for p in participants:
        role = p["role"]

        if role in EXECUTIVE_ROLES:
            send(
                p["email"],
                f"[{project_key}] Executive Project Summary",
                global_html
            )
            sent["executives"].append(p["email"])
        else:
            send(
                p["email"],
                f"[{project_key}] Meeting Update",
                combined_html
            )
            sent["participants"].append(p["email"])

    smtp.quit()

    return {
        "status": "success",
        "project_key": project_key,
        "participant_db_used": participant_db_path,
        "sent_to_participants": sent["participants"],
        "sent_to_executives": sent["executives"]
    }


