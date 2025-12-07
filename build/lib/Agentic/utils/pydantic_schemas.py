from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid




# PARTICIPANT SCHEMA
class Participant(BaseModel):
    name: str
    email: str
    role: str
    department: str


# SUMMARY POINTS SCHEMA
class SummaryList(BaseModel):
    project_key: str
    project_name: str
    meeting_name: str
    participants: List[str]
    summary_points: List[str]



# USER ANALYSIS AGENT
class UserSummary(BaseModel):
    participant_name: str
    key_updates: List[str] = Field(..., max_length=5)
    roadblocks: List[str] = Field(..., max_length=5)
    actionable: List[str] = Field(..., max_length=5)


class UsersAnalysis(BaseModel):
    project_key: str
    meeting_name: str
    participant_summary: UserSummary


