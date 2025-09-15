import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.schemas import ContextPacket, ProjectContext
from session_service.interview_state import InterviewState
from orchestrator_service.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_run_interview_flow(monkeypatch):
    call_order = []

    async def fake_execute(task_name, system_prompt, user_prompt=None):
        call_order.append(task_name)
        if task_name == "stage_0_analysis":
            return {
                "role_from_jd": "backend",
                "jd_core_skills": ["python", "db"],
                "resume_claims": ["python"],
                "overlap_skills": ["python"],
                "primary_overlap_focus": "python",
            }
        if task_name == "stage_1_parse":
            if "goal" in system_prompt:
                return {"goal": "demo", "constraints": ["latency"]}
            return {"scale_latency_slo": "100rps"}
        if task_name == "stage_2_parse":
            return {
                "skill_hooks": ["python", "db"],
                "notes": ["api work"],
                "evaluation_metrics": {"latency": "100ms"},
                "followup_hooks": ["redis"],
            }
        if task_name == "stage_3_question":
            if "python" in system_prompt:
                return {"question_text": "What is Python?"}
            return {"question_text": "What is a database?"}
        if task_name == "stage_3_eval":
            return {"result": "pass", "rationale": "ok"}
        if task_name == "stage_4_summary":
            return {"strengths": ["reasoning"], "risks": [], "follow_ups": []}
        raise AssertionError(task_name)

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = ContextPacket(
        jd_text="JD",
        resume_text="Resume",
        selected_project="demo project",
        project_context=ProjectContext(scale_latency_slo="100rps"),
        notes=["Initial answer"],
    )

    result = await ai.run_interview(packet)

    assert result.project_context.goal == "demo"
    assert result.skill_hooks == ["python", "db"]
    assert result.followup_hooks == ["redis"]
    assert result.resolved_followup_hooks == []
    assert result.project_context.evaluation_metrics == {"latency": "100ms"}
    assert [v.skill for v in result.verifications] == ["redis"]
    assert call_order == [
        "stage_0_analysis",
        "stage_1_parse",
        "stage_1_parse",
        "stage_2_parse",
        "stage_3_question",
        "stage_3_eval",
        "stage_4_summary",
    ]


@pytest.mark.asyncio
async def test_experience_plan_respected(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        if task_name == "question_generation":
            return {"question_text": "Question"}
        if task_name == "stage_1_parse":
            return {"goal": "demo", "constraints": []}
        if task_name == "skill_tag_refinement":
            return {"tags": []}
        raise AssertionError(task_name)

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = ContextPacket(
        jd_text="JD",
        resume_text="Resume",
        selected_project="demo",
        experience_plan=["components_list", "project_overview"],
    )
    state = InterviewState(packet)
    orch = Orchestrator()

    first = await orch.loop(state)
    assert first["question_type"] == "evidence_components_list"

    second = await orch.loop(state, "listed components")
    assert second["question_type"] == "warmup_project_overview"
