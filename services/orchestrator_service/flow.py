"""LangGraph orchestration for interview stages."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .schemas import ContextPacket, VerificationResult
from .programs.stage0_analysis import Stage0AnalysisProgram, JDResumeAnalysisInput
from .programs.stage3_theory import (
    TheoryQuestionProgram,
    TheoryQuestionInput,
    TheoryEvalProgram,
    TheoryEvalInput,
)
from .programs.stage4_wrapup import WrapUpProgram, WrapUpInput


InterviewState = ContextPacket


async def stage0_analysis_node(state: InterviewState) -> dict:
    """Analyze job description and resume to seed context."""
    program = Stage0AnalysisProgram()
    output = await program(
        JDResumeAnalysisInput(jd_text=state.jd_text, resume_text=state.resume_text)
    )
    return output.model_dump()


async def stage3_theory_node(state: InterviewState) -> dict:
    """Run a theory check on each collected skill in sequence."""
    skills = state.followup_hooks or state.skill_hooks or state.jd_core_skills
    if not skills:
        return {}

    idx = len(state.verifications)
    if idx >= len(skills):
        return {}

    skill = skills[idx]
    question = await TheoryQuestionProgram()(TheoryQuestionInput(skill=skill))
    eval_result = await TheoryEvalProgram()(TheoryEvalInput(answer=""))
    verification = VerificationResult(
        skill=skill, result=eval_result.result, rationale=eval_result.rationale
    )
    return {
        "verifications": state.verifications + [verification],
        "notes": state.notes + [question.question_text],
    }


async def stage4_wrapup_node(state: InterviewState) -> dict:
    """Summarize interview outcomes."""
    output = await WrapUpProgram()(WrapUpInput(notes=state.notes, verifications=state.verifications))
    return output.model_dump()


def build_interview_graph() -> StateGraph:
    """Create a sequential LangGraph covering all interview stages."""
    graph = StateGraph(InterviewState)
    graph.add_node("stage0_analysis", stage0_analysis_node)
    graph.add_node("stage3_theory", stage3_theory_node)
    graph.add_node("stage4_wrapup", stage4_wrapup_node)

    graph.add_edge(START, "stage0_analysis")
    graph.add_edge("stage0_analysis", "stage3_theory")

    def _more_theory(state: InterviewState) -> str:
        skills = state.followup_hooks or state.skill_hooks or state.jd_core_skills
        return "again" if len(state.verifications) < len(skills) else "done"

    graph.add_conditional_edges(
        "stage3_theory",
        _more_theory,
        {"again": "stage3_theory", "done": "stage4_wrapup"},
    )

    graph.add_edge("stage4_wrapup", END)

    return graph.compile()
