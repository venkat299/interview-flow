"""LangGraph orchestration for interview stages."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .schemas import ContextPacket, VerificationResult
from .programs.stage0_analysis import Stage0AnalysisProgram, JDResumeAnalysisInput
from .programs.stage1_warmup import (
    WarmupOverviewProgram,
    WarmupOverviewInput,
    WarmupConstraintProgram,
    WarmupConstraintInput,
)
from .programs.stage2_evidence import EvidenceProgram, EvidenceInput
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


async def stage1_warmup_node(state: InterviewState) -> dict:
    """Parse warm-up responses into project context."""
    overview = await WarmupOverviewProgram()(WarmupOverviewInput(answer=state.selected_project or ""))
    constraint = await WarmupConstraintProgram()(WarmupConstraintInput(answer=state.project_context.scale_latency_slo or ""))
    ctx = state.project_context.model_copy()
    ctx.goal = overview.goal
    ctx.constraints = overview.constraints
    ctx.scale_latency_slo = constraint.scale_latency_slo
    return {"project_context": ctx.model_dump()}


async def stage2_evidence_node(state: InterviewState) -> dict:
    """Extract evidence details from candidate answer."""
    answer = state.notes[-1] if state.notes else ""
    output = await EvidenceProgram()(EvidenceInput(answer=answer))
    return {
        "skill_hooks": output.skill_hooks,
        "confidence_ratings": output.confidence_ratings,
        "notes": state.notes + output.notes,
    }


async def stage3_theory_node(state: InterviewState) -> dict:
    """Run a theory check on each collected skill in sequence."""
    if not state.skill_hooks:
        return {}

    idx = len(state.verifications)
    if idx >= len(state.skill_hooks):
        return {}

    skill = state.skill_hooks[idx]
    confidence = state.confidence_ratings.get(skill, 3)
    question = await TheoryQuestionProgram()(TheoryQuestionInput(skill=skill, confidence=confidence))
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
    graph.add_node("stage1_warmup", stage1_warmup_node)
    graph.add_node("stage2_evidence", stage2_evidence_node)
    graph.add_node("stage3_theory", stage3_theory_node)
    graph.add_node("stage4_wrapup", stage4_wrapup_node)

    graph.add_edge(START, "stage0_analysis")
    graph.add_edge("stage0_analysis", "stage1_warmup")
    graph.add_edge("stage1_warmup", "stage2_evidence")
    graph.add_edge("stage2_evidence", "stage3_theory")

    def _more_theory(state: InterviewState) -> str:
        skills = state.skill_hooks or state.jd_core_skills
        return "again" if len(state.verifications) < len(skills) else "done"

    graph.add_conditional_edges(
        "stage3_theory",
        _more_theory,
        {"again": "stage3_theory", "done": "stage4_wrapup"},
    )

    graph.add_edge("stage4_wrapup", END)

    return graph.compile()
