import os
import re
from datetime import datetime
from pymongo import MongoClient
from pathlib import Path
from rapidfuzz import fuzz
import docx2txt
from dotenv import load_dotenv

load_dotenv()


def extract_transcripts(file_paths):
    """
    Extracts text from .txt, .docx, and .pdf files and returns
    one unified cleaned transcript string.
    """

    collected = []

    for fp in file_paths:
        fp = Path(fp)
        ext = fp.suffix.lower()

        # -------------------------
        # TXT
        # -------------------------
        if ext == ".txt":
            text = fp.read_text(encoding="utf-8", errors="ignore")
            collected.append(clean_text(text))

        # -------------------------
        # DOCX
        # -------------------------
        elif ext == ".docx":
            text = docx2txt.process(str(fp))
            collected.append(clean_text(text))

        # -------------------------
        # PDF
        # -------------------------
        elif ext == ".pdf":
            try:
                from pdfminer.high_level import extract_text as pdf_extract
                text = pdf_extract(str(fp))
                collected.append(clean_text(text))
            except ImportError:
                raise ImportError("Install pdfminer.six to extract PDF text.")

        else:
            print(f"[Skipping] Unsupported file format: {fp}")

    # combine all transcripts
    transcript = "\n\n".join(collected)
    return transcript.strip()


# ===================================================================================================

def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)   # collapse big gaps
    text = re.sub(r"[ \t]+", " ", text)     # remove excessive spacing
    return text.strip()


# ===================================================================================================

def process_transcript(transcript):
    """
    Processes a meeting transcript text and extracts key information.
    """

    first_line = transcript.split("\n")[0].strip()

    Meeting_name = first_line.replace("-Meeting Recording", "").strip()

    Project_name = first_line.replace("-Meeting Recording", "").strip()
    Project_name = re.sub(r"-\d{8}_\d{6}", "", Project_name).strip()

    # Duration
    m = re.search(r"(\d{1,2}m\s?\d{1,2}s)", transcript)
    Duration = m.group(1) if m else ""

    # Participants Extraction
    participants = set()
    matches = re.findall(r"([A-Z][a-zA-Z]+\s[A-Z][a-zA-Z]+)\s\d+:\d{2}", transcript)
    for name in matches:
        first, last = name.split()
        if len(first) >= 3 and len(last) >= 3:
            participants.add(f"{first} {last}")
    Participants_list = sorted(list(participants))

    # Date-time Extraction
    dt_match = re.search(r"\b(\d{1,2}\s[A-Za-z]+\s\d{4}),\s(\d{1,2}:\d{2}[ap]m)\b", transcript)
    if dt_match:
        dt = datetime.strptime(f"{dt_match.group(1)} {dt_match.group(2)}",
                               "%d %B %Y %I:%M%p")
        Date_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        Date_time = ""

    Project_key = f"{Project_name} - {', '.join(Participants_list)}"

    return {
        "Project_key": Project_key,
        "Project_name": Project_name,
        "Meeting_name": Meeting_name,
        "Participants_list": Participants_list,
        "Date_time": Date_time,
        "Duration": Duration,
        "Full_Transcript": transcript
    }


# ===================================================================================================


def add_transcript_to_mongo(transcript_path,
                            mongo_uri=os.getenv("MONGO_URI")):
    """
    Extracts transcript → processes metadata → inserts into OMNI_MEET_DB.Raw_Transcripts.
    Stores participants as NAME ONLY.
    """

    transcript = extract_transcripts([transcript_path])
    meta = process_transcript(transcript)

    client = MongoClient(mongo_uri)
    db_name = "OMNI_MEET_DB"
    coll_name = "Raw_Transcripts"

    db = client[db_name]
    collection = db[coll_name]

    project_key = meta["Project_key"].strip()
    project_name = meta["Project_name"]
    meeting_name = meta["Meeting_name"]

    participants_list = meta["Participants_list"]

    new_meeting = {
        "meeting_name": meeting_name,
        "meeting_time": meta["Date_time"],
        "duration": meta["Duration"],
        "participants": participants_list,
        "Transcript": [meta["Full_Transcript"]],
        "processed": False
    }

    # ----------------------------------------
    # Try matching project using fuzzy match
    # ----------------------------------------
    existing_projects = list(collection.find({}, {"Project_key": 1, "_id": 1}))

    matched_project_key = None
    matched_project_id = None

    for p in existing_projects:
        existing_key = p.get("Project_key", "")
        score = fuzz.ratio(project_key.lower(), existing_key.lower())
        if score >= 90:
            matched_project_key = existing_key
            matched_project_id = p.get("_id")
            break

    # --------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------
    if matched_project_key:
        full_project = collection.find_one(
            {"_id": matched_project_id},
            {"meetings.meeting_name": 1}
        )

        existing_meetings = full_project.get("meetings", [])
        for mt in existing_meetings:
            if mt.get("meeting_name") == meeting_name:
                return (
                    f"transcript already exists at _id: [{matched_project_id}] with project_key [{project_key}] "
                    f"and meeting_name [{meeting_name}]"
                )

    # --------------------------------------------------
    # CASE 1: Append to existing project
    # --------------------------------------------------
    if matched_project_key:
        collection.update_one(
            {"_id": matched_project_id},
            {
                "$set": {"Project_name": project_name},
                "$push": {"meetings": new_meeting}
            }
        )

        return (
            f"Added new meeting to existing project into with _id: [{matched_project_id}] into [{db_name}.{coll_name}], "
            f"and project_key is [{matched_project_key}]"
        )

    # --------------------------------------------------
    # CASE 2: Create new project document (NO project_id)
    # --------------------------------------------------
    new_doc = {
        "Project_key": project_key,
        "Project_name": project_name,
        "meetings": [new_meeting]
    }

    result = collection.insert_one(new_doc)

    return (
        f"Created new project with _id: [{result.inserted_id}] into [{db_name}.{coll_name}] "
        f"and Project_key is [{project_key}]"
    )
