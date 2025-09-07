import sys
import sys
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from session_service.interview_state import InterviewState
from session_service.service import ConnectionManager


@pytest.mark.asyncio
async def test_topic_progression(monkeypatch):
    blueprint = {"topics": [
        {"name": "python", "relevance_to_role": 10},
        {"name": "databases", "relevance_to_role": 8},
    ]}
    state = InterviewState(blueprint)

    first = state.get_next_topic()
    assert first["name"] == "python"
    state.update_state_after_answer({"score": 8})

    second = state.get_next_topic()
    assert second["name"] == "databases"
    state.update_state_after_answer({"score": 8})

    third = state.get_next_topic()
    assert third["name"] == "python"
    assert state.topic_progress["python"] == 2


@pytest.mark.asyncio
async def test_next_question_has_feedback(monkeypatch):
    async def fake_generate(request):
        return "What is Python?"

    monkeypatch.setattr(
        "session_service.service.generate_next_question",
        fake_generate,
    )
    # Force deterministic feedback
    monkeypatch.setattr(
        "session_service.service.random.choice",
        lambda opts: "Great, let's move on.",
    )

    mgr = ConnectionManager()
    websocket = object()
    mgr.contexts[websocket] = {"job_description": ""}
    mgr.persona[websocket] = "friendly_mentor"
    state = InterviewState({"topics": [{"name": "python", "relevance_to_role": 10}]})
    state.current_phase = "technical"
    state.current_topic = state.get_next_topic()
    mgr.states[websocket] = state

    question = await mgr._next_question(websocket, [])
    assert question.startswith("Great, let's move on.")


@pytest.mark.asyncio
async def test_lower_difficulty_after_poor_answer():
    blueprint = {"topics": [{"name": "python", "relevance_to_role": 10}]}
    state = InterviewState(blueprint)
    state.get_next_topic()
    state.switch_after = 99
    state.update_state_after_answer({"score": 8})
    assert state.topic_progress["python"] == 2
    state.update_state_after_answer({"score": 2})
    assert state.topic_progress["python"] == 1


@pytest.mark.asyncio
async def test_switch_topic_after_threshold():
    blueprint = {"topics": [
        {"name": "python", "relevance_to_role": 10},
        {"name": "databases", "relevance_to_role": 8},
    ]}
    state = InterviewState(blueprint)
    state.get_next_topic()
    state.switch_after = 2
    state.update_state_after_answer({"score": 8})
    assert not state.should_switch_topic()
    state.update_state_after_answer({"score": 8})
    assert state.should_switch_topic()
    state.get_next_topic()
    assert state.current_topic["name"] == "databases"
