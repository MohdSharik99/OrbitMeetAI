import re
from datetime import datetime
import hashlib
import json
import os
from pymongo import MongoClient
from rapidfuzz import fuzz

def process_transcript(transcript):
    """
    Processes a meeting transcript text and extracts key information.
    """

    first_line = transcript.split("\n")[0].strip()

    Meeting_name = first_line.replace("-Meeting Recording", "").strip()

    Project_name = first_line.replace("-Meeting Recording", "").strip()
    Project_name = re.sub(r"-\d{8}_\d{6}", "", Project_name).strip()

    m = re.search(r"(\d{1,2}m\s?\d{1,2}s)", transcript)
    Duration = m.group(1) if m else ""

    participants = set()
    matches = re.findall(r"([A-Z][a-zA-Z]+\s[A-Z][a-zA-Z]+)\s\d+:\d{2}", transcript)
    for name in matches:
        first, last = name.split()
        if len(first) >= 3 and len(last) >= 3:
            participants.add(f"{first} {last}")
    Participants_list = sorted(list(participants))

    dt_match = re.search(r"\b(\d{1,2}\s[A-Za-z]+\s\d{4}),\s(\d{1,2}:\d{2}[ap]m)\b", transcript)
    if dt_match:
        dt = datetime.strptime(f"{dt_match.group(1)} {dt_match.group(2)}", "%d %B %Y %I:%M%p")
        Date_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        Date_time = ""

    Project_key = f"{Project_name} - {', '.join(Participants_list)}"

    hash_input = f"{Project_name}|{','.join(Participants_list)}".encode("utf-8")
    Project_id = hashlib.sha256(hash_input).hexdigest()[:12]

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
    Extracts transcript → processes metadata → inserts into OMNI_MEET_DB.Raw_Transcripts.
    Stores participants as NAME ONLY (no email, no role, no dept).
    """

    transcript = extract_transcripts([transcript_path])
    meta = process_transcript(transcript)

    client = MongoClient(mongo_uri)
    db = client["OMNI_MEET_DB"]
    collection = db["Raw_Transcripts"]

    project_key = meta["Project_key"].strip()
    project_id = meta["Project_id"]
    project_name = meta["Project_name"]

    # -------------------------------
    # PARTICIPANTS = NAME ONLY
    # -------------------------------
    participants_list = meta["Participants_list"]  # ["Lisa Chen", "Ben Carter", ...]

    # -------------------------------
    # Build meeting entry
    # -------------------------------
    new_meeting = {
        "meeting_name": meta["Meeting_name"],
        "meeting_time": meta["Date_time"],
        "duration": meta["Duration"],
        "participants": participants_list,           # <-- names only
        "Transcript": [meta["Full_Transcript"]],
        "processed": False
    }

    # -------------------------------
    # Try matching project using fuzzy match
    # -------------------------------
    existing = list(collection.find({}, {"Project_key": 1, "_id": 0}))
    matched_project = None

    for project in existing:
        existing_key = project.get("Project_key", "")
        score = fuzz.ratio(project_key.lower(), existing_key.lower())
        if score >= 90:
            matched_project = project
            break

    # -------------------------------
    # CASE 1 — Append to existing project
    # -------------------------------
    if matched_project:
        collection.update_one(
            {"Project_key": matched_project["Project_key"]},
            {
                "$set": {"Project_name": project_name},
                "$push": {"meetings": new_meeting}
            }
        )
        print(f"Added new meeting to existing project: {matched_project['Project_key']}")
        return matched_project["Project_key"]

    # -------------------------------
    # CASE 2 — Create new project document
    # -------------------------------
    new_doc = {
        "Project_key": project_key,
        "Project_id": project_id,
        "Project_name": project_name,
        "meetings": [new_meeting]
    }

    collection.insert_one(new_doc)
    print(f"Created new project with Project_key: {project_key}")

    return project_key
