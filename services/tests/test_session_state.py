import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.schemas import ContextPacket
from session_service.interview_state import InterviewState


@pytest.mark.asyncio
async def test_context_packet_creation(monkeypatch):
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
            return {"tags": ["python"]}
        raise AssertionError(f"Unexpected task {task_name}")

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    assert isinstance(packet, ContextPacket)
    assert packet.role_from_jd == "backend"
    assert packet.role_skill_tags == ["scaling", "caching", "python"]
    assert packet.time_remaining_min == packet.duration_min


def test_stage_progression_and_time():
    packet = ContextPacket(jd_text="", resume_text="", duration_min=10)
    packet.time_remaining_min = 10
    state = InterviewState(packet)
    assert state.current_phase == "warm_up"
    state.advance_phase()
    assert state.current_phase == "evidence"
    state.decrement_time(3)
    assert state.packet.time_remaining_min == 7

