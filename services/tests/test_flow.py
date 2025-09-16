import pytest

from orchestrator_service import llm_api as ai
from orchestrator_service.schemas import ContextPacket
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
        if task_name == "stage_1_intro":
            return {"question_text": "Welcome! Tell me about yourself."}
        if task_name == "stage_2_focus_plan":
            return {
                "interview_focus_areas": [
                    {
                        "area_name": "Python Mastery",
                        "reasoning_questions": [
                            "Why do you enjoy working with Python?",
                            "How have you improved a Python service?",
                        ],
                        "conceptual_questions": [
                            "What is a virtual environment?",
                            "Explain list comprehensions.",
                        ],
                    }
                ]
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

    packet = ContextPacket(jd_text="JD", resume_text="Resume")

    result = await ai.run_interview(packet)

    assert call_order == [
        "stage_0_analysis",
        "stage_1_intro",
        "stage_2_focus_plan",
        "stage_3_question",
        "stage_3_eval",
        "stage_3_question",
        "stage_3_eval",
        "stage_4_summary",
    ]


