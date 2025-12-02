from datetime import datetime

from pydantic import BaseModel, Field
from typing import List, Optional
import uuid



class AgentInput(BaseModel):
    input: str

# METADATA SCHEMA
class Participant(BaseModel):
    name: str
    email: str
    role: str
    department: str


class MeetingMetadata(BaseModel):
    project_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    meeting_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_name: Optional[str]
    meeting_name: str
    meeting_time: datetime
    duration: str
    participants: List[Participant]

class SummaryAnalysis(BaseModel):
    metadata: MeetingMetadata
    summary: List[str] = Field(..., max_length=10)

# USER ANALYSIS AGENT

class UserAnalysis(BaseModel):
    participant_name: str
    key_updates: List[str] = Field(..., max_length=5)
    roadblocks: List[str] = Field(..., max_length=5)
    actionable: List[str] = Field(..., max_length=5)

# COMBINED MEETING ANALYSIS (One per meeting)
class MeetingAnalysis(BaseModel):
    metadata: MeetingMetadata  # One metadata object
    user_analyses: List[UserAnalysis]  # Analysis for each participant


