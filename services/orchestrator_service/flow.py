"""LangGraph orchestration for interview stages."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .schemas import ContextPacket
from .programs.stage0_analysis import Stage0AnalysisProgram, JDResumeAnalysisInput
from .programs.stage1_intro import Stage1IntroProgram, IntroModuleInput
from .programs.stage2_qa import Stage2QAProgram, Stage2QAInput
from .programs.stage4_wrapup import WrapUpProgram, WrapUpInput


InterviewState = ContextPacket


async def stage0_analysis_node(state: InterviewState) -> dict:
    """Analyze job description and resume to seed context."""
    program = Stage0AnalysisProgram()
    output = await program(
        JDResumeAnalysisInput(jd_text=state.jd_text, resume_text=state.resume_text)
    )
    return output.model_dump()


async def stage1_intro_node(state: InterviewState) -> dict:
    """Generate a greeting and capture it for reference."""

    program = Stage1IntroProgram()
    output = await program(IntroModuleInput(role=state.role_from_jd))
    return {"notes": state.notes + [output.question_text]}


async def stage2_focus_plan_node(state: InterviewState) -> dict:
    """Request focus areas and questions for the QA stage."""

    program = Stage2QAProgram()
    output = await program(
        Stage2QAInput(jd_text=state.jd_text, resume_text=state.resume_text)
    )
    return {"focus_areas": output.interview_focus_areas}


async def stage4_wrapup_node(state: InterviewState) -> dict:
    """Summarize interview outcomes."""
    output = await WrapUpProgram()(WrapUpInput(notes=state.notes, verifications=state.verifications))
    return output.model_dump()


def build_interview_graph() -> StateGraph:
    """Create a sequential LangGraph covering all interview stages."""
    graph = StateGraph(InterviewState)
    graph.add_node("stage0_analysis", stage0_analysis_node)
    graph.add_node("stage1_intro", stage1_intro_node)
    graph.add_node("stage2_focus_plan", stage2_focus_plan_node)
    graph.add_node("stage4_wrapup", stage4_wrapup_node)

    graph.add_edge(START, "stage0_analysis")
    graph.add_edge("stage0_analysis", "stage1_intro")
    graph.add_edge("stage1_intro", "stage2_focus_plan")
    graph.add_edge("stage2_focus_plan", "stage4_wrapup")

    graph.add_edge("stage4_wrapup", END)

    return graph.compile()
