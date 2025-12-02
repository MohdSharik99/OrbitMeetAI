from langchain.agents import create_agent
from langchain.tools import BaseTool
from typing import List
from datetime import datetime
import json
import uuid

# Import your Pydantic schemas
from src.utils.pydantic_schemas import MeetingAnalysis, UserAnalysis, MeetingMetadata, Participant

# Import your utils
from src.utils.tools import detect_and_normalize_transcript
from src.ArchiveFiles.StanderdizedTranscriptTool import convert_transcript_to_teams_format
from src.ArchiveFiles.MetadataTool import extract_meeting_metadata

# System prompt defining the agent's role
SYSTEM_PROMPT = """You are a Meeting Analysis Agent.
You take a meeting transcript (any format) as input and produce a structured analysis in MeetingAnalysis format.

Workflow:
1. If the input is a file, use detect_and_normalize_transcript to extract and normalize text.
2. Convert the transcript to MS Teams format using convert_transcript_to_teams_format.
3. Extract meeting metadata using extract_meeting_metadata.
4. Analyze participant contributions, identifying updates, roadblocks, and actionable items.

Return the final result in JSON format strictly following the MeetingAnalysis Pydantic schema.
"""

class MeetingAnalysisAgent:
    def __init__(self, llm, tools: List[BaseTool]):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}

        # Create the agent directly (no AgentExecutor needed)
        self.agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )

    def analyze_meeting(self, input_data: str) -> MeetingAnalysis:
        """Process transcript and return MeetingAnalysis object"""
        try:
            # Directly invoke the agent
            result = self.agent.invoke({"input": input_data})

            # Extract JSON string from agent result
            analysis_json = self._extract_json(result)

            # Convert JSON into Pydantic MeetingAnalysis
            return self._parse_meeting_analysis(analysis_json)

        except Exception as e:
            print(f"Error in Meeting Analysis Agent: {e}")
            return self._create_default_analysis()

    def _extract_json(self, text: str) -> str:
        """Extract JSON object from text (simple regex)"""
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group() if match else text

    def _parse_meeting_analysis(self, analysis_json: str) -> MeetingAnalysis:
        """Convert JSON string to Pydantic object"""
        data = json.loads(analysis_json)

        # Build MeetingMetadata
        metadata_data = data.get('metadata', {})
        participants = [
            Participant(
                name=p['name'],
                email=p.get('email', ''),
                role=p.get('role', ''),
                department=p.get('department', '')
            ) for p in metadata_data.get('participants', [])
        ]
        metadata = MeetingMetadata(
            project_id=uuid.UUID(metadata_data.get('project_id')) if metadata_data.get('project_id') else uuid.uuid4(),
            meeting_id=uuid.UUID(metadata_data.get('meeting_id')) if metadata_data.get('meeting_id') else uuid.uuid4(),
            project_name=metadata_data.get('project_name'),
            meeting_name=metadata_data.get('meeting_name', 'Meeting Analysis'),
            meeting_time=datetime.fromisoformat(metadata_data['meeting_time']) if metadata_data.get('meeting_time') else datetime.now(),
            duration=metadata_data.get('duration', 'Unknown'),
            participants=participants
        )

        # Build UserAnalyses
        user_analyses = [
            UserAnalysis(
                participant_name=u['participant_name'],
                updates=u.get('updates', []),
                roadblocks=u.get('roadblocks', []),
                actionable=u.get('actionable', [])
            ) for u in data.get('user_analyses', [])
        ]

        return MeetingAnalysis(metadata=metadata, user_analyses=user_analyses)

    def _create_default_analysis(self) -> MeetingAnalysis:
        """Fallback MeetingAnalysis if processing fails"""
        return MeetingAnalysis(
            metadata=MeetingMetadata(
                project_id=uuid.uuid4(),
                meeting_id=uuid.uuid4(),
                project_name=None,
                meeting_name="Meeting Analysis",
                meeting_time=datetime.now(),
                duration="Unknown",
                participants=[]
            ),
            user_analyses=[]
        )

# Factory function to create the agent (optional)
def create_meeting_analysis_agent(llm):
    tools = [
        detect_and_normalize_transcript,
        convert_transcript_to_teams_format,
        extract_meeting_metadata
    ]
    return MeetingAnalysisAgent(llm, tools)
