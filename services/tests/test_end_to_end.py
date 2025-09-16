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
        if task_name == "stage_1_intro":
            return {"question_text": "Welcome!"}
        if task_name == "stage_2_focus_plan":
            return {
                "interview_focus_areas": [
                    {
                        "area_name": "Python Mastery",
                        "reasoning_questions": [
                            "Why do you enjoy Python?",
                            "How have you optimized Python code?",
                        ],
                        "conceptual_questions": [
                            "What is PEP 8?",
                            "Explain the GIL.",
                        ],
                    }
                ]
            }
        if task_name == "question_generation":
            assert "thanks the candidate" in system_prompt.lower()
            assert "warm compliment" in system_prompt.lower()
            return {
                "question_text": "Thanks for your time today — your Python insights were impressive. Could you share how this interview felt for you?"
            }
        if task_name == "stage_4_summary":
            return {"strengths": ["reasoning"], "risks": [], "follow_ups": []}
        return {}

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    packet = await ai.analyze_jd_resume("JD", "Resume")
    state = InterviewState(packet)
    orch = Orchestrator()

    q1 = await orch.loop(state)
    assert q1["question_type"] == "intro_greeting"

    q2 = await orch.loop(state, "Intro answer")
    assert q2["question_type"] == "qa_reasoning"
    assert q2.get("focus_area") == "Python Mastery"

    q3 = await orch.loop(state, "Reasoning 1")
    assert q3["question_type"] == "qa_reasoning"

    q4 = await orch.loop(state, "Reasoning 2")
    assert q4["question_type"] == "qa_conceptual"

    q5 = await orch.loop(state, "Conceptual 1")
    assert q5["question_type"] == "qa_conceptual"

    q6 = await orch.loop(state, "Conceptual 2")
    assert q6["question_type"] == "wrapup_feedback"
    assert "thanks" in q6["question_text"].lower()

    q7 = await orch.loop(state, "Great experience!")
    assert q7 is None

    assert state.packet.time_remaining_min == 0

