import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.schemas import ContextPacket, ProjectContext


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
    assert [v.skill for v in result.verifications] == ["python", "db"]
    assert call_order == [
        "stage_0_analysis",
        "stage_1_parse",
        "stage_1_parse",
        "stage_2_parse",
        "stage_3_question",
        "stage_3_eval",
        "stage_3_question",
        "stage_3_eval",
        "stage_4_summary",
    ]
