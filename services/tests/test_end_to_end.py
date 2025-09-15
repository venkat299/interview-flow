import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.schemas import ContextPacket
from orchestrator_service.orchestrator import Orchestrator
from session_service.interview_state import InterviewState


@pytest.mark.asyncio
async def test_run_interview_end_to_end(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        if task_name == "stage_0_analysis":
            return {
                "role_from_jd": "backend",
                "jd_core_skills": ["python"],
                "resume_claims": ["python"],
                "overlap_skills": ["python"],
                "primary_overlap_focus": "python",
            }
        if task_name == "skill_tag_refinement":
            return {"tags": []}
        if task_name == "stage_3_question":
            return {"question_text": "What is Python?"}
        if task_name == "stage_3_eval":
            return {"result": "pass", "rationale": "ok"}
        if task_name == "question_generation":
            return {"question_text": "feedback?"}
        if task_name == "stage_4_summary":
            return {"strengths": ["reasoning"], "risks": [], "follow_ups": []}
        return {}

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    state = InterviewState(packet)
    orch = Orchestrator()

    q1 = await orch.loop(state)
    assert q1["question_type"] == "theory_primary"

    q2 = await orch.loop(state, "Answer")
    assert q2["question_type"] == "theory_followup"

    q3 = await orch.loop(state, "Answer2")
    assert q3["question_type"] == "wrapup_feedback"

    q4 = await orch.loop(state, "feedback")
    assert q4["question_type"] == "wrapup_closing"

    q5 = await orch.loop(state)
    assert q5 is None
    assert state.packet.time_remaining_min == 0

