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

# METADATA SCHEMA
class MeetingMetadata(BaseModel):
    project_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    meeting_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_name: Optional[str]
    meeting_name: str
    meeting_time: datetime
    duration: str
    participants: List[Participant]


# SUMMARY POINTS SCHEMA
class SummaryList(BaseModel):
    project_id: Optional[uuid.UUID] = None
    meeting_id: Optional[uuid.UUID] = None
    summary_points: List[str]



# USER ANALYSIS AGENT
class UserSummary(BaseModel):
    participant_name: str
    key_updates: List[str] = Field(..., max_length=5)
    roadblocks: List[str] = Field(..., max_length=5)
    actionable: List[str] = Field(..., max_length=5)


# USER ANALYSIS AGENT
class UsersAnalysis(BaseModel):
    project_id: Optional[uuid.UUID] = None
    meeting_id: Optional[uuid.UUID] = None
    participant_summary: UserSummary


# Combined schema
class MeetingAnalysis(BaseModel):
    metadata: MeetingMetadata
    summary: SummaryList
    user_analysis: List[UsersAnalysis]


