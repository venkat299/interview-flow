import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.orchestrator import Orchestrator
from session_service.interview_state import InterviewState


@pytest.mark.asyncio
async def test_stage_flow(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        mapping = {
            "stage_0_analysis": {
                "role_from_jd": "backend",
                "jd_core_skills": ["python"],
                "resume_claims": ["python"],
                "overlap_skills": ["python"],
                "primary_overlap_focus": "python",
            },
            "stage_1_parse": {
                "goal": "demo",
                "constraints": ["latency"],
                "scale_latency_slo": "100rps",
            },
            "stage_2_parse": {
                "skill_hooks": ["python"],
                "confidence_ratings": {"python": 5},
                "notes": ["api work"],
            },
            "stage_3_question": {"question_text": "What is Python?"},
            "stage_3_eval": {"result": "pass", "rationale": "ok"},
            "stage_4_summary": {"strengths": ["reasoning"], "risks": [], "follow_ups": []},
        }
        return mapping[task_name]

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    state = InterviewState(packet)
    orch = Orchestrator()

    q1 = await orch.loop(state)
    assert "overview" in q1.lower()

    q2 = await orch.loop(state, "Built service")
    assert "hardest constraint" in q2.lower()

    q3 = await orch.loop(state, "Latency shaped design")
    assert "components you directly built" in q3.lower()

    q4 = await orch.loop(state, "API using python confidence 5")
    assert q4 == "What is Python?"

    q5 = await orch.loop(state, "A language")
    assert q5 == "Any questions about the role, roadmap, or stack?"

    q6 = await orch.loop(state, "No questions")
    assert q6 is None
    assert state.packet.time_remaining_min == 0

