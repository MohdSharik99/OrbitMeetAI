# src/backend/utils/db_updates.py

import os
from pymongo import MongoClient
from bson import ObjectId
import certifi

def mark_meeting_processed_safe(document_id: str, meeting_name: str) -> bool:
    """
    Safely mark a meeting as processed using arrayFilters instead of index.
    """
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI not configured")

    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
    db = client["OMNI_MEET_DB"]
    col = db["Raw_Transcripts"]

    res = col.update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "meetings.$[m].processed": True
            }
        },
        array_filters=[{"m.meeting_name": meeting_name}]
    )

    return res.modified_count > 0
