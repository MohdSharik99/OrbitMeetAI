import re
from datetime import datetime
import hashlib
import docx2txt
from pathlib import Path
import json
import os
from pymongo import MongoClient
from rapidfuzz import fuzz

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


# ----------------------
# HELPER: clean text
# ----------------------
def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)   # collapse big gaps
    text = re.sub(r"[ \t]+", " ", text)     # remove excessive spacing
    return text.strip()


def process_transcript(transcript):
    """
    Processes a meeting transcript text and extracts key information:
    - Project name
    - Meeting name
    - Participants
    - Duration
    - Date and time
    - Project key (human-readable)
    - Project ID (hash)
    Returns a dictionary with all these fields plus the full transcript.
    """

    # Get the first line of the transcript
    first_line = transcript.split("\n")[0].strip()

    # Extract meeting name (keep timestamp if present, remove suffix)
    Meeting_name = first_line.replace("-Meeting Recording", "").strip()

    # Extract project name (remove timestamp + suffix)
    Project_name = first_line.replace("-Meeting Recording", "").strip()
    Project_name = re.sub(r"-\d{8}_\d{6}", "", Project_name).strip()

    # Extract duration (e.g., "51m 18s")
    m = re.search(r"(\d{1,2}m\s?\d{1,2}s)", transcript)
    Duration = m.group(1) if m else ""

    # Extract participants (names like "Lisa Chen")
    participants = set()
    matches = re.findall(r"([A-Z][a-zA-Z]+\s[A-Z][a-zA-Z]+)\s\d+:\d{2}", transcript)
    for name in matches:
        first, last = name.split()
        if len(first) >= 3 and len(last) >= 3:
            participants.add(f"{first} {last}")
    Participants_list = sorted(list(participants))

    # Extract date and time (format: "2025-12-10 15:00:00")
    dt_match = re.search(r"\b(\d{1,2}\s[A-Za-z]+\s\d{4}),\s(\d{1,2}:\d{2}[ap]m)\b", transcript)
    if dt_match:
        dt = datetime.strptime(f"{dt_match.group(1)} {dt_match.group(2)}", "%d %B %Y %I:%M%p")
        Date_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        Date_time = ""

    # Create a human-readable project key
    Project_key = f"{Project_name} - {', '.join(Participants_list)}"

    # Generate a stable project ID using a SHA-256 hash
    hash_input = f"{Project_name}|{','.join(Participants_list)}".encode("utf-8")
    Project_id = hashlib.sha256(hash_input).hexdigest()[:12]  # shorten to 12 chars

    # Return all extracted information in a dictionary
    return {
        "Project_key": Project_key,
        "Project_id": Project_id,
        "Project_name": Project_name,
        "Meeting_name": Meeting_name,
        "Participants_list": Participants_list,
        "Date_time": Date_time,
        "Duration": Duration,
        "Full_Transcript": transcript
    }



# =====================================================================================================================



def add_transcript_to_mongo(transcript_path, mongo_uri="mongodb://localhost:27017"):
    """
    Adds a new transcript to MongoDB.
    'transcript' is a raw string.
    """

    transcript = extract_transcripts([transcript_path])

    # Process raw transcript to structured dict
    transcript_dict = process_transcript(transcript)

    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]
    collection = db["Raw_Transcripts"]

    new_project_key = transcript_dict["Project_key"]
    new_project_id = transcript_dict["Project_id"]

    # Fuzzy match against existing projects
    existing_projects = list(collection.find({}, {"Project_key": 1, "_id": 1}))
    matched_project = None
    for project in existing_projects:
        score = fuzz.ratio(new_project_key, project.get("Project_key", ""))
        if score >= 90:
            matched_project = project
            break

    # Prepare new meeting entry
    new_meeting = {
        "meeting_name": transcript_dict["Meeting_name"],
        "meeting_time": transcript_dict["Date_time"],
        "duration": transcript_dict["Duration"],
        "participants": transcript_dict["Participants_list"],
        "Transcript": [transcript_dict["Full_Transcript"]]
    }

    if matched_project:
        # Add to existing project using Project_key
        collection.update_one(
            {"Project_key": matched_project["Project_key"]},
            {"$push": {"meetings": new_meeting}}
        )
        print(f"Added new meeting to existing project: {matched_project['Project_key']}")
    else:
        # Create a new project document
        new_doc = {
            "Project_key": new_project_key,
            "Project_id": new_project_id,
            "Project_name": transcript_dict["Project_name"],
            "meetings": [new_meeting]
        }
        collection.insert_one(new_doc)
        print(f"Created new project with Project_id: {new_project_id}")





