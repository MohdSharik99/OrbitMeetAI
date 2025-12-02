from langchain.tools import tool
from pydantic_schemas import MeetingMetadata

@tool
def extract_meeting_metadata(transcript: str) -> str:
    """
    Extract structured meeting metadata from transcript.
    Returns JSON string that can be parsed into MeetingMetadata.
    The agent's LLM will perform the actual analysis when calling this tool.
    """
    from langchain_core.output_parsers import PydanticOutputParser

    parser = PydanticOutputParser(pydantic_object=MeetingMetadata)

    special_instructions = """
SPECIAL PARSING INSTRUCTIONS:
- meeting_time: Extract from timestamp patterns like 20251130_093000 → 30 November 2025, 09:30am
- project_name: Extract from meeting titles before timestamps, avoid part1, followup etc.
- meeting_name: Same as project_name but can be a followup, part1, part2, etc.
- duration: Extract from the next line of meeting_time like 51m 18s, 30m 15s 
- participants: Extract names from speaker lines and infer roles from context

Example: "Project Phoenix -Part 1-20251130_093000-Meeting Recording" should parse as:
- project_name: "Project Phoenix"
- meeting_name: "Project Phoenix - Part 1
- meeting_time: "30 November 2025, 09:30am"
- meeting_name: "Meeting Recording"
"""

    return f"{special_instructions}\n\nReturn in this format: {parser.get_format_instructions()}"