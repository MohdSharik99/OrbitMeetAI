from langchain.tools import tool
from langchain_core.messages import SystemMessage

# Define the system prompt with all instructions and examples
SYSTEM_PROMPT = """Convert any transcript to MS Teams format if not already formatted:

FIRST: If already in MS Teams format (**Title**, **Speaker** MM:SS), return as-is.

TARGET FORMAT:
**Title**
Date & Time
Duration  
Transcription Starter

**Speaker** MM:SS
Message
[empty line between speakers]

CONVERSION RULES:
- If already in MS Teams format, return as-is
- Timestamps: [HH:MM:SS] → MM:SS, HH:MM:SS AM/PM → MM:SS, SPEAKER_01 (HH:MM:SS) → MM:SS
- Speakers: SPEAKER_01 → Speaker 1, John D. → John, merge multi-line text
- Metadata: Extract from headers or use defaults
- Defaults: "Meeting Transcript", "Date not specified", "Duration not specified", "System started transcription"
- No timestamps? Start at 0:04, increment by 10s

EXPECTED OUTPUT EXAMPLES:

Example 1:
**Project Nexus Launch Retrospective & Q2 Planning-20251203_150000-Meeting Recording**
03 December 2025, 03:00pm
51m 18s
CHEN, Lisa started transcription

**Lisa Chen** 0:03
Okay, I think we're all here. Good afternoon everyone. Let's begin. As you know, Project Nexus officially launched last Tuesday, and today we're here to do a thorough retrospective and start looking ahead to Q2. I want this to be an honest, constructive conversation.

**Ben Carter** 0:20
Afternoon, Lisa. Team.



Example 2:
**Project Phoenix - Sprint 15 Planning & Tech Deep Dive-20251130_093000-Meeting Recording**
30 November 2025, 09:30am
31m 15s
PATEL, Priya started transcription

**Priya Patel** 0:02
Okay, I think everyone's here. Good morning, team. Let's get started. Thanks for making it. The agenda for today is sprint 15 planning, a deep dive on the new user authentication migration, and then open floor for any blockers.

**Ben Carter** 0:15
Morning, Priya. Everyone. Ready to go.



INPUT EXAMPLES (Different formats you might receive):

Input (Zoom): [00:00:05] Alice: Hello
Input (Webex): 10:05:15 AM John: Message  
Input (Speaker Diarization): SPEAKER_00 (00:00:05): Let's begin
Input (Already formatted): **Meeting**\nDate\nDuration\nStarter\n\n**John** 0:05\nMessage

All should convert to the TARGET FORMAT shown above.

Now convert this transcript:

{transcript}

Output:"""


# LangChain tool version
@tool
def convert_transcript_to_teams_format(transcript_text: str) -> str:
    """
    Convert various transcript formats to consistent MS Teams-compatible format.

    Args:
        transcript_text: Raw transcript text in various formats

    Returns:
        str: Formatted transcript in consistent MS Teams format
    """
    # This would be implemented with your actual LLM call
    # For now, return the formatted prompt
    return SYSTEM_PROMPT.format(transcript=transcript_text)




# Example usage
if __name__ == "__main__":
    # Example transcript
    test_transcript = """
    Project Review-20251218_110000
    18 December 2025, 11:00am
    35m 00s
    DOE, Jane started transcription

    [00:00:03] Emily Zhang: Let's review the Q1 roadmap.
    [00:00:12] Ryan Patel: The timeline looks aggressive but achievable.
    """


    # Show the tool usage
    result = convert_transcript_to_teams_format.invoke(test_transcript)
    print("Tool Output Preview:")
    print(result[:500] + "..." if len(result) > 500 else result)