import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest

from ai_orchestration_service import ai_orchestration as ai
from ai_orchestration_service.schemas import (
    InterviewContext,
    ConversationTurn,
    InterviewRequest,
    InterviewBlueprintResponse,
    TopicBlueprint,
    EvaluationRequest,
    EvaluationResponse,
)


@pytest.mark.asyncio
async def test_generate_question(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "question_generation"
        return {"question_text": "What is your experience with Python?"}

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    req = InterviewRequest(
        context=InterviewContext(job_description="Backend developer"),
        history=[ConversationTurn(role="candidate", message="Hi")],
        current_topic="python",
        current_difficulty=3,
        persona="friendly_mentor",
    )

    question = await ai.generate_next_question(req)
    assert question == "What is your experience with Python?"


@pytest.mark.asyncio
async def test_generate_question_with_hint_and_type(monkeypatch):
    """Ensure dynamic prompt includes hint instruction and question type."""

    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "question_generation"
        assert "subtle hint" in system_prompt
        assert "Question Type" in system_prompt
        return {"question_text": "Sample question", "question_type": "yes/no"}

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    req = InterviewRequest(
        context=InterviewContext(job_description="Backend"),
        history=[],
        current_topic="python",
        current_difficulty=1,
        persona="friendly_mentor",
        needs_hint=True,
    )

    question = await ai.generate_next_question(req)
    assert question == "Sample question"


@pytest.mark.asyncio
async def test_create_interview_blueprint(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "blueprint_generation"
        return {
            "interview_title": "Backend Developer Interview",
            "experience_level": "Senior",
            "topics": [
                {
                    "name": "python",
                    "relevance_to_role": 10,
                    "required_depth": "Advanced",
                    "jd_context": ["python"],
                    "resume_evidence": ["python"],
                }
            ],
        }

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    blueprint = await ai.create_interview_blueprint(
        InterviewContext(job_description="Backend dev", candidate_resume="Python exp")
    )

    assert isinstance(blueprint, InterviewBlueprintResponse)
    assert blueprint.interview_title == "Backend Developer Interview"
    assert blueprint.topics[0].name == "python"


@pytest.mark.asyncio
async def test_evaluate_candidate_answer(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "answer_evaluation"
        return {
            "score": 8,
            "assessed_depth": "Intermediate",
            "llm_confidence": "High",
            "justification": "Solid answer",
            "is_truthful": True,
        }

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    tb = TopicBlueprint(
        name="python",
        relevance_to_role=10,
        required_depth="Intermediate",
        jd_context=["python"],
        resume_evidence=["python"],
    )
    req = EvaluationRequest(
        question="What is Python?",
        answer="A programming language",
        topic_blueprint=tb,
    )

    resp = await ai.evaluate_candidate_answer(req)
    assert isinstance(resp, EvaluationResponse)
    assert resp.score == 8


@pytest.mark.asyncio
async def test_generate_introductory_question(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "question_generation"
        assert "introduce themselves" in system_prompt
        return {"question_text": "Tell me about yourself."}

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    question = await ai.generate_introductory_question()
    assert question == "Tell me about yourself."


@pytest.mark.asyncio
async def test_generate_soft_skill_question(monkeypatch):
    async def fake_execute(task_name, system_prompt, user_prompt=None):
        assert task_name == "question_generation"
        assert "Resume: My Resume" in system_prompt
        return {"question_text": "Describe a time you worked on a team."}

    monkeypatch.setattr(ai.gateway, "execute_task", fake_execute)

    question = await ai.generate_soft_skill_question("My Resume")
    assert question == "Describe a time you worked on a team."
