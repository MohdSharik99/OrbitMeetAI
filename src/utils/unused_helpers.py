# Currently in this project we assume that every transctipt is in MS Team format. But in case if we
# receiving file that is not in the desired format here are a couple additional function that we can use

import re
import docx2txt
from pathlib import Path
from langchain.tools import tool
#========================================================================================
# When it is in .docx, .txt, .pdf extension format we can use this function to store into a variable
# ======================================================================================


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



# -----------------------------
# LangChain Tool
# -----------------------------
@tool
def format_normalize_tool(file_path: str) -> str:
    """
    Detect transcript file format and convert to standardized text format.

    Args:
        file_path: Path to the transcript file

    Returns:
        str: Normalized text content in consistent format
    """
    try:
        return process_file(file_path)
    except Exception as e:
        return f"Error processing file: {str(e)}"
## =================================================================================
# here is a Langchain tool that can convert any other format (like Google Meet, Zoom format to MS teams format)
# ====================================================================================================



###################################### ORBIT MEET FORMAT TOOL ####################################

from langchain.tools import tool
from langchain_core.messages import SystemMessage

# Define the system prompt with all instructions and examples
SYSTEM_PROMPT = """Convert any transcript to ORBIT MEET (Same as MS Teams) format if not already formatted:

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
def orbit_meet_tool(transcript_text: str) -> str:
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

