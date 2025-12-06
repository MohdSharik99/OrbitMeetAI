from typing import List, Dict, Any, Optional
from functools import partial
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

# Import your schemas
from src.utils.pydantic_schemas import SummaryList, UsersAnalysis


# ==============================================================
# ORCHESTRATOR STATE (Pydantic Model)
# ==============================================================
class OrchestratorState(BaseModel):
    transcript: str
    project_key: str
    project_id: str
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


# ==============================================================
# AGENT NODES (Async)
# ==============================================================

async def run_summary_agent(state: OrchestratorState, summary_agent):
    points = await summary_agent.agenerate_summary(state.transcript)
    return state.model_copy(update={"summary_points": points})


def build_summary_object(state: OrchestratorState):
    summary_obj = SummaryList(
        project_key=state.project_key,
        project_id=state.project_id,
        project_name=state.project_name,
        meeting_name=state.meeting_name,
        participants=state.participants,
        summary_points=state.summary_points
    )
    return state.model_copy(update={"summary_obj": summary_obj})


async def run_participant_agent(state: OrchestratorState, participant_agent):
    participant_summaries = await participant_agent.aparticipant_analysis(
        state.transcript
    )
    return state.model_copy(update={"participant_summaries": participant_summaries})


def build_user_analysis_list(state: OrchestratorState):
    ua_list = [
        UsersAnalysis(
            project_key=state.project_key,
            project_id=state.project_id,
            meeting_name=state.meeting_name,
            participant_summary=ps
        )
        for ps in state.participant_summaries
    ]

    return state.model_copy(update={"user_analysis_list": ua_list})


# ==============================================================
# TOOL NODES (Async)
# ==============================================================

async def save_summary_to_db(state: OrchestratorState, save_tool):
    await save_tool.ainvoke({
        "core_agent": "summary",
        "project_key": state.project_key,
        "project_id": state.project_id,
        "project_name": state.project_name,
        "meeting_name": state.meeting_name,
        "data": state.summary_obj.model_dump()
    })
    return state


async def save_participant_summary_to_db(state: OrchestratorState, save_tool):
    await save_tool.ainvoke({
        "core_agent": "participant_summary",
        "project_key": state.project_key,
        "project_id": state.project_id,
        "project_name": state.project_name,
        "meeting_name": state.meeting_name,
        "data": [ua.model_dump() for ua in state.user_analysis_list]
    })
    return state


async def fetch_project_data(state: OrchestratorState, fetch_tool):
    project_data = await fetch_tool.ainvoke({
        "project_key": state.project_key
    })
    return state.model_copy(update={"project_data": project_data})


async def run_global_summary(state: OrchestratorState, global_agent):
    global_summary = await global_agent.agenerate_project_summary(
        state.project_data
    )
    return state.model_copy(update={"global_summary": global_summary})


async def send_emails(state: OrchestratorState, email_tool):
    meeting_text = "\n".join(state.summary_points)

    participant_text = "\n".join([
        f"{ua.participant_summary.participant_name} | "
        f"Updates: {', '.join(ua.participant_summary.key_updates)} "
        f"Roadblocks: {', '.join(ua.participant_summary.roadblocks)} "
        f"Actionable: {', '.join(ua.participant_summary.actionable)}"
        for ua in state.user_analysis_list
    ])

    global_text = state.global_summary

    await email_tool.ainvoke(
        {
            "project_key": state.project_key,
            "meeting_summary_text": meeting_text,
            "participant_analysis_text": participant_text,
            "global_summary_text": global_text,
        },
        # <- NOW READ FROM STATE, NOT HARDCODED
        participant_db_path=state.participant_db_path
    )

    return state



# ==============================================================
# BUILD LANGGRAPH WORKFLOW (Async Mode)
# ==============================================================

def build_orchestrator_graph(
    summary_agent,
    participant_agent,
    global_summary_agent,
    save_tool,
    fetch_tool,
    email_tool
):
    workflow = StateGraph(OrchestratorState)

    # ---- Agent Nodes ----
    workflow.add_node("summary",
        partial(run_summary_agent, summary_agent=summary_agent)
    )

    workflow.add_node("build_summary", build_summary_object)

    workflow.add_node("participant",
        partial(run_participant_agent, participant_agent=participant_agent)
    )

    workflow.add_node("build_user_analysis", build_user_analysis_list)

    # ---- Tool Nodes ----
    workflow.add_node("save_summary",
        partial(save_summary_to_db, save_tool=save_tool)
    )

    workflow.add_node("save_participant",
        partial(save_participant_summary_to_db, save_tool=save_tool)
    )

    workflow.add_node("fetch",
        partial(fetch_project_data, fetch_tool=fetch_tool)
    )

    workflow.add_node("global_summary",
        partial(run_global_summary, global_agent=global_summary_agent)
    )

    workflow.add_node(
        "email",
        partial(send_emails, email_tool=email_tool)
    )

    # ---- Edges ----
    workflow.add_edge("summary", "build_summary")
    workflow.add_edge("build_summary", "participant")
    workflow.add_edge("participant", "build_user_analysis")
    workflow.add_edge("build_user_analysis", "save_summary")
    workflow.add_edge("save_summary", "save_participant")
    workflow.add_edge("save_participant", "fetch")
    workflow.add_edge("fetch", "global_summary")
    workflow.add_edge("global_summary", "email")
    workflow.add_edge("email", END)

    # Compile in async mode
    return workflow.compile()
