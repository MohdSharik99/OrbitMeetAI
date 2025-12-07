"""
OrbitMeetAI Chatbot - Simple document-based chatbot using MongoDB Raw Transcripts.
Fetches full transcripts from MongoDB and uses LLM for question answering.
"""
import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import certifi
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

load_dotenv()

# ======================================================================
# LOGGER CONFIGURATION
# ======================================================================
logger.remove()  # remove default
logger.add(
    sink=lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level}</level> | "
           "<cyan>{message}</cyan>"
)

# ======================================================================
# GLOBAL STATE
# ======================================================================
mongo_uri = os.getenv("MONGO_URI")
chatbot_instances: Dict[str, Any] = {}  # Cache chatbot chains by project_id


# ======================================================================
# FETCH FULL TRANSCRIPT TEXT FROM MONGODB
# ======================================================================
def fetch_project_transcript_text(project_id: str) -> str:
    """
    Fetch full transcript text for a given project_id from MongoDB Raw_Transcripts collection.
    Combines all meeting transcripts into a single text string.
    
    Args:
        project_id: MongoDB ObjectId as string
        
    Returns:
        Combined transcript text from all meetings
    """
    if not mongo_uri:
        raise ValueError("MONGO_URI not configured")
    
    try:
        # Validate ObjectId
        try:
            object_id = ObjectId(project_id)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format: {project_id}")
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Fetch document
        doc = collection.find_one({"_id": object_id})
        
        if not doc:
            raise ValueError(f"Project with id '{project_id}' not found")
        
        project_name = doc.get("Project_name", "Unknown Project")
        meetings = doc.get("meetings", [])
        
        # Combine all transcripts into a single text
        transcript_parts = []
        transcript_parts.append(f"Project: {project_name}\n")
        transcript_parts.append("=" * 80 + "\n\n")
        
        for meeting in meetings:
            meeting_name = meeting.get("meeting_name", "Unknown Meeting")
            meeting_time = meeting.get("meeting_time", "")
            participants = meeting.get("participants", [])
            transcript_list = meeting.get("Transcript", [])
            
            # Get transcript text (first element if list, or the value itself)
            transcript_text = ""
            if transcript_list:
                if isinstance(transcript_list, list):
                    transcript_text = transcript_list[0] if transcript_list else ""
                else:
                    transcript_text = str(transcript_list)
            
            if transcript_text:
                transcript_parts.append(f"Meeting: {meeting_name}\n")
                transcript_parts.append(f"Time: {meeting_time}\n")
                transcript_parts.append(f"Participants: {', '.join(participants) if participants else 'N/A'}\n")
                transcript_parts.append("-" * 80 + "\n")
                transcript_parts.append(f"Transcript:\n{transcript_text}\n")
                transcript_parts.append("=" * 80 + "\n\n")
        
        full_text = "".join(transcript_parts)
        logger.info(f"Fetched transcript text for project '{project_name}' ({len(full_text)} characters)")
        return full_text
    
    except Exception as e:
        logger.error(f"Error fetching transcript text: {e}")
        raise


# ======================================================================
# BUILD SIMPLE CHATBOT CHAIN
# ======================================================================
def build_chatbot_chain() -> Any:
    """
    Build a simple chatbot chain using prompt | llm | StrOutputParser.
    Similar to the example provided - no RAG, just direct document context.
    
    Returns:
        LangChain chain (prompt | llm | StrOutputParser)
    """
    # Initialize LLM
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.3,
        api_key=api_key
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_template("""
You are a helpful AI assistant for meeting analysis. You must answer ONLY from the document content given below.

If you are not sure what to answer, then apologize and ask for clarification. Say "I don't know based on the document."

Document:
{document}

User Question:
{question}
""")
    
    # Create simple chain: prompt | llm | StrOutputParser
    chain = prompt | llm | StrOutputParser()
    
    return chain





# ======================================================================
# INITIALIZE CHATBOT
# ======================================================================
def initialize_chatbot(project_id: str, force_refresh: bool = False):
    """
    Initialize or retrieve a chatbot chain for a given project.
    Fetches transcript text and builds a simple chain (no RAG).
    
    Args:
        project_id: MongoDB ObjectId as string
        force_refresh: If True, refetch transcript even if cached
        
    Returns:
        Dictionary with 'chain' and 'document_text'
    """
    # Check cache
    if project_id in chatbot_instances and not force_refresh:
        logger.info(f"Using cached chatbot for project {project_id}")
        return chatbot_instances[project_id]
    
    logger.info(f"Initializing chatbot for project {project_id}")
    
    # Fetch full transcript text from MongoDB
    document_text = fetch_project_transcript_text(project_id)
    
    if not document_text or len(document_text.strip()) == 0:
        raise ValueError(f"No transcript text found for project {project_id}")
    
    # Build simple chain
    chain = build_chatbot_chain()
    
    # Cache the instance (chain + document text)
    chatbot_instances[project_id] = {
        "chain": chain,
        "document_text": document_text
    }
    
    logger.success(f"Chatbot initialized for project {project_id}")
    return chatbot_instances[project_id]


# ======================================================================
# CHAT FUNCTION
# ======================================================================
async def chat_with_project(project_id: str, question: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
    """
    Chat with the project chatbot using simple document-based approach (no RAG).
    
    Args:
        project_id: MongoDB ObjectId as string
        question: User's question
        chat_history: Optional list of previous messages for context (not used in simple approach)
        
    Returns:
        Dictionary with answer and metadata
    """
    try:
        # Initialize chatbot (gets chain + document text)
        chatbot_data = initialize_chatbot(project_id)
        chain = chatbot_data["chain"]
        document_text = chatbot_data["document_text"]
        
        # Invoke chain with document and question
        answer = await chain.ainvoke({
            "document": document_text,
            "question": question
        })
        
        logger.info(f"Generated answer for question: '{question[:50]}...'")
        
        # Extract meeting names from document text for sources
        sources = []
        if "Meeting:" in document_text:
            import re
            meeting_matches = re.findall(r"Meeting: ([^\n]+)", document_text)
            sources = list(set(meeting_matches))
        
        return {
            "answer": answer,
            "sources": sources,
            "project_id": project_id
        }
    
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise


# ======================================================================
# FIND PROJECT BY NAME
# ======================================================================
def find_project_by_name(project_name: str) -> Optional[str]:
    """
    Find project_id (ObjectId) by project name.
    
    Args:
        project_name: Project name to search for
        
    Returns:
        Project ID (ObjectId as string) or None if not found
    """
    if not mongo_uri:
        raise ValueError("MONGO_URI not configured")
    
    try:
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Search for project by name (case-insensitive)
        doc = collection.find_one(
            {"Project_name": {"$regex": project_name, "$options": "i"}}
        )
        
        if doc:
            return str(doc["_id"])
        
        return None
    
    except Exception as e:
        logger.error(f"Error finding project: {e}")
        raise

