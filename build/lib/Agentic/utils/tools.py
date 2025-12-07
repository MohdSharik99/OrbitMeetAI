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
def send_project_emails(
    input_data: Dict[str, Any],
    participant_db_path: str = "participants_data.csv",
) -> Dict[str, Any]:
    """
    Sends formatted OrbitMeetAI emails using `src/utils/meeting_email.html`.
    """

    import os, csv, ssl, smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from datetime import datetime

    # ----------------------------
    # Extract data
    # ----------------------------
    meeting_name = input_data["meeting_name"]
    project_name = input_data["project_name"]

    meeting_text = input_data["meeting_summary_text"]
    participant_text = input_data["participant_analysis_text"]
    global_text = input_data["global_summary_text"]

    # ----------------------------
    # Load HTML template file
    # ----------------------------
    template_path = os.path.join("src", "utils", "meeting_email.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_html = f.read()

    # ----------------------------
    # Convert text → HTML bullets (for meeting summary)
    # ----------------------------
    def to_bullets(text: str) -> str:
        items = [
            f"<li>{line.strip()}</li>"
            for line in text.split("\n")
            if line.strip()
        ]
        return "<ul>" + "".join(items) + "</ul>"
    
    # ----------------------------
    # Format participant analysis as structured cards
    # ----------------------------
    def format_participant_analysis(participant_text: str) -> str:
        """
        Formats participant analysis text into structured HTML cards.
        Expected format: "Name | Updates: ... Roadblocks: ... Actionable: ..."
        """
        if not participant_text.strip():
            return ""
        
        cards = []
        # Split by participant (assuming each line is a participant)
        for line in participant_text.split("\n"):
            if not line.strip() or " | " not in line:
                continue
            
            # Parse the line: "Name | Updates: ... Roadblocks: ... Actionable: ..."
            parts = line.split(" | ", 1)
            if len(parts) < 2:
                continue
            
            participant_name = parts[0].strip()
            rest = parts[1].strip()
            
            # Extract Updates, Roadblocks, Actionable using regex for better parsing
            import re
            
            updates = []
            roadblocks = []
            actionable = []
            
            # Extract Updates
            updates_match = re.search(r'Updates:\s*(.+?)(?:\s+Roadblocks:|$)', rest, re.IGNORECASE)
            if updates_match:
                updates_str = updates_match.group(1).strip()
                updates = [u.strip() for u in updates_str.split(",") if u.strip()]
            
            # Extract Roadblocks
            roadblocks_match = re.search(r'Roadblocks:\s*(.+?)(?:\s+Actionable:|$)', rest, re.IGNORECASE)
            if roadblocks_match:
                roadblocks_str = roadblocks_match.group(1).strip()
                roadblocks = [r.strip() for r in roadblocks_str.split(",") if r.strip()]
            
            # Extract Actionable
            actionable_match = re.search(r'Actionable:\s*(.+?)$', rest, re.IGNORECASE)
            if actionable_match:
                actionable_str = actionable_match.group(1).strip()
                actionable = [a.strip() for a in actionable_str.split(",") if a.strip()]
            
            # Skip if no data found
            if not (updates or roadblocks or actionable):
                continue
            
            # Build participant card HTML
            card_html = f"""
            <div class="participant-card">
                <div class="participant-name">{participant_name}</div>
            """
            
            if updates:
                card_html += f"""
                <div class="participant-section">
                    <div class="participant-section-label">📊 Key Updates</div>
                    <div class="participant-section-content">
                        <ul>
                            {''.join([f'<li>{update}</li>' for update in updates])}
                        </ul>
                    </div>
                </div>
                """
            
            if roadblocks:
                card_html += f"""
                <div class="participant-section">
                    <div class="participant-section-label">⚠️ Roadblocks</div>
                    <div class="participant-section-content">
                        <ul>
                            {''.join([f'<li>{roadblock}</li>' for roadblock in roadblocks])}
                        </ul>
                    </div>
                </div>
                """
            
            if actionable:
                card_html += f"""
                <div class="participant-section">
                    <div class="participant-section-label">✅ Action Items</div>
                    <div class="participant-section-content">
                        <ul>
                            {''.join([f'<li>{action}</li>' for action in actionable])}
                        </ul>
                    </div>
                </div>
                """
            
            card_html += "</div>"
            cards.append(card_html)
        
        if not cards:
            return ""
        
        return f"""
        <div class="section">
            <h2 class="section-title">👥 Participant Analysis</h2>
            {''.join(cards)}
        </div>
        """
    
    # ----------------------------
    # Format global summary (for executives)
    # ----------------------------
    def format_global_summary(global_text: str) -> str:
        """Formats global summary with proper HTML structure"""
        if not global_text.strip():
            return ""
        
        # Preserve line breaks and format
        formatted = global_text.strip().replace("\n\n", "\n")
        
        return f"""
        <div class="section">
            <h2 class="section-title">📊 Executive Project Summary</h2>
            <div class="executive-summary">
                <div class="section-content">{formatted}</div>
            </div>
        </div>
        """

    meeting_html = to_bullets(meeting_text)

    # ----------------------------
    # Load participants
    # ----------------------------
    participants = []
    with open(participant_db_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            participants.append({
                "name": row["EmployeeName"],
                "email": row["EmployeeEmail"],
                "role": row["Role"].lower().strip()
            })

    EXEC_ROLES = {
        "manager", "senior manager", "director",
        "vp", "vice president", "chief",
        "head", "lead"
    }

    # ----------------------------
    # SMTP (SSL)
    # ----------------------------
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    context = ssl.create_default_context()

    sent = {"participants": [], "executives": []}

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)

        def send_formatted(to_email: str, html: str):
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Meeting Summary: {meeting_name} | {project_name}"
            msg["From"] = f"OrbitMeetAI <{SMTP_EMAIL}>"
            msg["To"] = to_email
            msg["Reply-To"] = SMTP_EMAIL  # Set reply-to to avoid no-reply issues
            msg.attach(MIMEText(html, "html"))
            smtp.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        for p in participants:
            name = p["name"]
            email = p["email"]
            is_exec = p["role"] in EXEC_ROLES

            # Insert dynamic blocks
            participant_section = ""
            executive_section = ""

            if is_exec:
                executive_section = format_global_summary(global_text)
                sent["executives"].append(email)
            else:
                participant_section = format_participant_analysis(participant_text)
                sent["participants"].append(email)

            # Build final email body
            html_body = template_html\
                .replace("{{receiver_name}}", name)\
                .replace("{{subject}}", meeting_name)\
                .replace("{{project_name}}", project_name)\
                .replace("{{meeting_summary}}", meeting_html)\
                .replace("{{participant_section}}", participant_section)\
                .replace("{{executive_section}}", executive_section)\
                .replace("{{year}}", str(datetime.now().year))

            send_formatted(email, html_body)

    return {
        "status": "success",
        "meeting_name": meeting_name,
        "sent_to_participants": sent["participants"],
        "sent_to_executives": sent["executives"]
    }
