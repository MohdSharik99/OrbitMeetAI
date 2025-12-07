from typing import List, Dict, Any, Optional
from functools import partial
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from loguru import logger

# Import your schemas
from src.Agentic.utils.pydantic_schemas import SummaryList, UsersAnalysis

# ======================================================================
# LOGURU CONFIGURATION
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
# ORCHESTRATOR STATE
# ======================================================================
class OrchestratorState(BaseModel):
    transcript: str
    project_key: str
    project_name: str
    meeting_name: str
    participants: List[str]

    summary_points: Optional[List[str]] = None
    participant_summaries: Optional[List[Any]] = None
    summary_obj: Optional[Any] = None
    user_analysis_list: Optional[List[Any]] = None

    project_data: Optional[Dict[str, Any]] = None
    global_summary: Optional[str] = None

    participant_db_path: Optional[str] = "participants_data.csv"


# ======================================================================
# AGENT NODES (ASYNC)
# ======================================================================

async def run_summary_agent(state: OrchestratorState, summary_agent):
    logger.info("Step 1: Running Meeting Summary Agent...")
    try:
        summary_points = await summary_agent.agenerate_summary(state.transcript)
        logger.success("Meeting Summary generated successfully.")
        return state.model_copy(update={"summary_points": summary_points})
    except Exception as e:
        logger.error(f"Error in Meeting Summary Agent: {e}")
        raise


def build_summary_object(state: OrchestratorState):
    logger.info("Step 2: Building SummaryList Pydantic object...")
    try:
        summary_obj = SummaryList(
            project_key=state.project_key,
            project_name=state.project_name,
            meeting_name=state.meeting_name,
            participants=state.participants,
            summary_points=state.summary_points
        )
        logger.success("SummaryList object created successfully.")
        return state.model_copy(update={"summary_obj": summary_obj})
    except Exception as e:
        logger.error(f"Error creating SummaryList: {e}")
        raise


async def run_participant_agent(state: OrchestratorState, participant_agent):
    logger.info("Step 3: Running Participant Analysis Agent...")
    try:
        participant_summaries = await participant_agent.aparticipant_analysis(
            state.transcript
        )
        logger.success("Participant Analysis generated successfully.")
        return state.model_copy(update={"participant_summaries": participant_summaries})
    except Exception as e:
        logger.error(f"Error in Participant Analysis Agent: {e}")
        raise


def build_user_analysis_list(state: OrchestratorState):
    logger.info("Step 4: Building UsersAnalysis list...")
    try:
        ua_list = [
            UsersAnalysis(
                project_key=state.project_key,
                meeting_name=state.meeting_name,
                participant_summary=ps
            )
            for ps in state.participant_summaries
        ]

        logger.success("UsersAnalysis list created successfully.")
        return state.model_copy(update={"user_analysis_list": ua_list})
    except Exception as e:
        logger.error(f"Error creating user analysis list: {e}")
        raise


# ======================================================================
# TOOL NODES (ASYNC)
# ======================================================================

async def save_summary_to_db(state: OrchestratorState, save_tool):
    logger.info("Step 5: Saving Meeting Summary to MongoDB...")
    try:
        await save_tool.ainvoke({
            "core_agent": "summary",
            "project_key": state.project_key,
            "project_name": state.project_name,
            "meeting_name": state.meeting_name,
            "data": state.summary_obj.model_dump()
        })
        logger.success("Meeting Summary saved successfully.")
        return state
    except Exception as e:
        logger.error(f"Error saving meeting summary: {e}")
        raise


async def save_participant_summary_to_db(state: OrchestratorState, save_tool):
    logger.info("Step 6: Saving Participant Analysis to MongoDB...")
    try:
        await save_tool.ainvoke({
            "core_agent": "participant_summary",
            "project_key": state.project_key,
            "project_name": state.project_name,
            "meeting_name": state.meeting_name,
            "data": [ua.model_dump() for ua in state.user_analysis_list]
        })
        logger.success("Participant Analysis saved successfully.")
        return state
    except Exception as e:
        logger.error(f"Error saving participant summary: {e}")
        raise


async def fetch_project_data(state: OrchestratorState, fetch_tool):
    logger.info("Step 7: Fetching Project History from MongoDB...")
    try:
        project_data = await fetch_tool.ainvoke({
            "project_key": state.project_key
        })
        logger.success("Project History fetched successfully.")
        return state.model_copy(update={"project_data": project_data})
    except Exception as e:
        logger.error(f"Error fetching project data: {e}")
        raise


async def run_global_summary(state: OrchestratorState, global_agent):
    logger.info("Step 8: Generating Global Project Summary...")
    try:
        global_summary = await global_agent.agenerate_project_summary(
            state.project_data
        )
        logger.success("Global Summary generated successfully.")
        return state.model_copy(update={"global_summary": global_summary})
    except Exception as e:
        logger.error(f"Error generating global summary: {e}")
        raise


async def save_project_summary_to_db(state: OrchestratorState, save_tool):
    logger.info("Step 9: Saving Project Summary to MongoDB...")
    try:
        await save_tool.ainvoke({
            "project_key": state.project_key,
            "project_name": state.project_name,
            "global_summary": state.global_summary
        })
        logger.success("Project Summary saved successfully.")
        return state
    except Exception as e:
        logger.error(f"Error saving project summary: {e}")
        raise


async def send_emails(state: OrchestratorState, email_tool):
    logger.info("Step 10: Sending Emails to participants & executives...")

    meeting_text = "\n".join(state.summary_points)

    participant_text = "\n".join([
        f"{ua.participant_summary.participant_name} | "
        f"Updates: {', '.join(ua.participant_summary.key_updates)} "
        f"Roadblocks: {', '.join(ua.participant_summary.roadblocks)} "
        f"Actionable: {', '.join(ua.participant_summary.actionable)}"
        for ua in state.user_analysis_list
    ])

    global_text = state.global_summary

    try:
        await email_tool.ainvoke({
            "input_data": {
                "project_key": state.project_key,
                "project_name": state.project_name,
                "meeting_name": state.meeting_name,
                "meeting_summary_text": meeting_text,
                "participant_analysis_text": participant_text,
                "global_summary_text": global_text,
            },
            "participant_db_path": state.participant_db_path
        })
        logger.success("Emails sent successfully.")
        return state
    except Exception as e:
        logger.error(f"Error sending emails: {e}")
        raise


# ======================================================================
# BUILD LANGGRAPH WORKFLOW (ASYNC)
# ======================================================================

def build_orchestrator_graph(
    summary_agent,
    participant_agent,
    global_summary_agent,
    save_tool,
    fetch_tool,
    save_project_summary_tool,
    email_tool
):
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("summary", partial(run_summary_agent, summary_agent=summary_agent))
    workflow.add_node("build_summary", build_summary_object)
    workflow.add_node("participant", partial(run_participant_agent, participant_agent=participant_agent))
    workflow.add_node("build_user_analysis", build_user_analysis_list)

    workflow.add_node("save_summary", partial(save_summary_to_db, save_tool=save_tool))
    workflow.add_node("save_participant", partial(save_participant_summary_to_db, save_tool=save_tool))
    workflow.add_node("fetch", partial(fetch_project_data, fetch_tool=fetch_tool))
    workflow.add_node("global_summary", partial(run_global_summary, global_agent=global_summary_agent))
    workflow.add_node("save_project_summary", partial(save_project_summary_to_db, save_tool=save_project_summary_tool))
    workflow.add_node("email", partial(send_emails, email_tool=email_tool))

    workflow.add_edge("__start__", "summary")

    workflow.add_edge("summary", "build_summary")
    workflow.add_edge("build_summary", "participant")
    workflow.add_edge("participant", "build_user_analysis")
    workflow.add_edge("build_user_analysis", "save_summary")
    workflow.add_edge("save_summary", "save_participant")
    workflow.add_edge("save_participant", "fetch")
    workflow.add_edge("fetch", "global_summary")
    workflow.add_edge("global_summary", "save_project_summary")
    workflow.add_edge("save_project_summary", "email")
    workflow.add_edge("email", END)

    return workflow.compile()
