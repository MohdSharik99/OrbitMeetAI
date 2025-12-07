"""
FastAPI application for OrbitMeetAI Orchestrator
"""
import os
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import certifi

# Import agents and orchestrator
from src.Agentic.agents.MeetingSummaryAgent import MeetingSummaryAnalyst
from src.Agentic.agents.ParticipantAnalystAgent import ParticipantSummaryAnalyst
from src.Agentic.agents.ProjectSummaryAgent import ProjectSummaryAnalyst
from src.Agentic.agents.Orchestrator import build_orchestrator_graph, OrchestratorState

# Import tools
from src.Agentic.utils import save_summaries_to_mongo, fetch_project_data_from_mongo, send_project_emails, save_project_summary_to_mongo

# Load environment variables
load_dotenv()

# ======================================================================
# GLOBAL STATE (Agents and Workflow)
# ======================================================================
agents = {}
workflow = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agents and workflow on startup, start scheduler"""
    global agents, workflow
    
    # Load API keys
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    # Initialize LLM
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.2,
        api_key=api_key
    )
    
    # Initialize agents
    agents["summary_agent"] = MeetingSummaryAnalyst(model=llm, tools=[])
    agents["participant_agent"] = ParticipantSummaryAnalyst(model=llm, tools=[])
    agents["global_agent"] = ProjectSummaryAnalyst(model=llm, tools=[])
    
    # Build orchestrator workflow
    workflow = build_orchestrator_graph(
        agents["summary_agent"],
        agents["participant_agent"],
        agents["global_agent"],
        save_summaries_to_mongo,
        fetch_project_data_from_mongo,
        save_project_summary_to_mongo,
        send_project_emails,
    )
    
    # Start background scheduler
    from src.backend.scheduler import start_scheduler
    start_scheduler()
    
    yield
    
    # Cleanup: Stop scheduler on shutdown
    from src.backend.scheduler import stop_scheduler
    stop_scheduler()


# ======================================================================
# FASTAPI APP
# ======================================================================
app = FastAPI(
    title="OrbitMeetAI API",
    description="API for meeting analysis and orchestration",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# REQUEST/RESPONSE MODELS
# ======================================================================
class ProcessMeetingRequest(BaseModel):
    """Request model for processing a meeting"""
    transcript: str = Field(..., description="Meeting transcript text")
    project_key: str = Field(..., description="Unique project identifier")
    project_name: str = Field(..., description="Project name")
    meeting_name: str = Field(..., description="Meeting name")
    participants: List[str] = Field(..., description="List of participant names")
    participant_db_path: Optional[str] = Field(
        default="SampleData/participants_database.csv",
        description="Path to participants database CSV file"
    )


class ProcessMeetingResponse(BaseModel):
    """Response model for processed meeting"""
    status: str = Field(..., description="Processing status")
    project_key: str = Field(..., description="Project key")
    meeting_name: str = Field(..., description="Meeting name")
    summary_points: Optional[List[str]] = Field(None, description="Meeting summary points")
    participant_summaries: Optional[List[Dict[str, Any]]] = Field(None, description="Participant analysis")
    global_summary: Optional[str] = Field(None, description="Global project summary")
    message: str = Field(..., description="Response message")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


class ProjectDataResponse(BaseModel):
    """Response for project data"""
    project_key: str
    project_name: str
    meetings: List[Dict[str, Any]]
    user_analysis: List[Dict[str, Any]]


class ChatRequest(BaseModel):
    """Request model for chat"""
    project_name: str = Field(..., description="Project name to chat about")
    question: str = Field(..., description="User's question")
    chat_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Optional chat history for context"
    )


class ChatResponse(BaseModel):
    """Response model for chat"""
    answer: str = Field(..., description="Chatbot's answer")
    sources: List[str] = Field(..., description="List of meeting names used as sources")
    project_id: str = Field(..., description="Project ID used")


# ======================================================================
# API ENDPOINTS
# ======================================================================
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "message": "OrbitMeetAI API is running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    if workflow is None:
        return {
            "status": "error",
            "message": "Workflow not initialized"
        }
    return {
        "status": "ok",
        "message": "Service is healthy"
    }


@app.post("/process-meeting", response_model=ProcessMeetingResponse)
async def process_meeting(request: ProcessMeetingRequest):
    """
    Process a meeting transcript through the orchestrator workflow.
    
    This endpoint:
    1. Generates meeting summary
    2. Analyzes participants
    3. Saves data to MongoDB
    4. Fetches project history
    5. Generates global project summary
    6. Sends emails to participants and executives
    """
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow not initialized. Please wait for service to start."
        )
    
    try:
        # Create initial state
        initial_state = OrchestratorState(
            transcript=request.transcript,
            project_key=request.project_key,
            project_name=request.project_name,
            meeting_name=request.meeting_name,
            participants=request.participants,
            participant_db_path=request.participant_db_path
        )
        
        # Run orchestrator workflow
        final_state = await workflow.ainvoke(initial_state)
        
        # Format participant summaries for response
        participant_summaries = None
        if final_state.get("user_analysis_list"):
            participant_summaries = [
                ua.model_dump() for ua in final_state["user_analysis_list"]
            ]
        
        return ProcessMeetingResponse(
            status="success",
            project_key=final_state["project_key"],
            meeting_name=final_state["meeting_name"],
            summary_points=final_state.get("summary_points"),
            participant_summaries=participant_summaries,
            global_summary=final_state.get("global_summary"),
            message=f"Meeting '{request.meeting_name}' processed successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing meeting: {str(e)}"
        )


@app.get("/project/{project_key}", response_model=ProjectDataResponse)
async def get_project_data(project_key: str):
    """
    Fetch complete project data from MongoDB.
    
    Returns meeting summaries and participant analysis for a given project.
    """
    try:
        project_data = await fetch_project_data_from_mongo.ainvoke({
            "project_key": project_key
        })
        
        if "error" in project_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=project_data["error"]
            )
        
        return ProjectDataResponse(
            project_key=project_data["project_key"],
            project_name=project_data["project_name"],
            meetings=project_data.get("meetings", []),
            user_analysis=project_data.get("user_analysis", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching project data: {str(e)}"
        )


@app.get("/project-by-id/{project_id}", response_model=ProjectDataResponse)
async def get_project_data_by_id(project_id: str):
    """
    Fetch complete project data from MongoDB using transcript ObjectId.
    
    This endpoint:
    1. Fetches the transcript document from Raw_Transcripts by _id
    2. Extracts the project_key from the document
    3. Returns complete project data (meeting summaries and participant analysis)
    
    Returns the same data structure as /project/{project_key} endpoint.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(project_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ObjectId format: {project_id}"
            )
        
        # Connect to MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MONGO_URI not configured"
            )
        
        client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
        db = client["OMNI_MEET_DB"]
        collection = db["Raw_Transcripts"]
        
        # Fetch document to get project_key
        doc = collection.find_one({"_id": object_id})
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcript with id '{project_id}' not found"
            )
        
        project_key = doc.get("Project_key")
        if not project_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project_key not found in transcript document"
            )
        
        # Fetch complete project data using the project_key
        project_data = await fetch_project_data_from_mongo.ainvoke({
            "project_key": project_key
        })
        
        if "error" in project_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=project_data["error"]
            )
        
        return ProjectDataResponse(
            project_key=project_data["project_key"],
            project_name=project_data["project_name"],
            meetings=project_data.get("meetings", []),
            user_analysis=project_data.get("user_analysis", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching project data: {str(e)}"
        )


@app.post("/trigger-scheduler", response_model=HealthResponse)
async def trigger_scheduler_manually():
    """
    Manually trigger the scheduler to process unprocessed meetings.
    
    Useful for testing or immediate processing without waiting for the hourly schedule.
    """
    try:
        from src.backend.scheduler import run_manual_check
        await run_manual_check()
        return {
            "status": "ok",
            "message": "Scheduler job triggered successfully. Check logs for details."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering scheduler: {str(e)}"
        )


@app.post("/orbit-chat", response_model=ChatResponse)
async def orbit_chat(request: ChatRequest):
    """
    Chat with OrbitMeetAI about a specific project.
    
    This endpoint:
    1. Finds the project by name
    2. Fetches all meeting transcripts from MongoDB
    3. Uses RAG (Retrieval Augmented Generation) with MongoDB Vector Search
    4. Returns answer with source meetings
    
    The chatbot uses Voyage AI embeddings and stores vectors in MongoDB.
    """
    try:
        from src.chatbot.orbit_chat import chat_with_project, find_project_by_name
        
        # Find project by name
        project_id = find_project_by_name(request.project_name)
        
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{request.project_name}' not found"
            )
        
        # Chat with project
        result = await chat_with_project(
            project_id=project_id,
            question=request.question,
            chat_history=request.chat_history
        )
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            project_id=result["project_id"]
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in chat: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

