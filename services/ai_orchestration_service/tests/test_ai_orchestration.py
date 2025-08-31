import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx
import pytest

from ai_orchestration_service import ai_orchestration as ai
from ai_orchestration_service.schemas import (
    InterviewContext,
    ConversationTurn,
    InterviewBlueprintResponse,
)
from ai_orchestration_service.config import settings


@pytest.mark.asyncio
async def test_generate_question(monkeypatch):
    original_post = httpx.AsyncClient.post

    async def fake_post(self, url, headers=None, json=None):
        if url == "https://api.openai.com/v1/chat/completions":
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "What is your experience with Python?"}}
                    ]
                },
                request=httpx.Request("POST", url),
            )
        return await original_post(self, url, headers=headers, json=json)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    settings.llm_provider = "openai"

    question = await ai.generate_next_question(
        InterviewContext(job_description="Backend developer"),
        [ConversationTurn(role="candidate", message="Hi")],
    )

    assert question == "What is your experience with Python?"



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
async def test_generate_next_question_uses_configured_timeout(monkeypatch):
    settings.llm_provider = "openai"
    settings.llm_timeout = 7.5

    captured = {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, headers=None, json=None):
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Example?"}}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)

    await ai.generate_next_question(
        InterviewContext(job_description="Backend developer"),
        [ConversationTurn(role="candidate", message="Hi")],
    )

    assert captured["timeout"] == settings.llm_timeout


@pytest.mark.asyncio
async def test_local_llm_url_defaults_to_http(monkeypatch):
    captured = {}

    async def fake_post(self, url, headers=None, json=None):
        captured["url"] = url
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Hi"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "local_llm_url", "localhost:9999/v1/chat/completions")

    question = await ai.generate_next_question(
        InterviewContext(job_description="Backend developer"),
        [],
    )

    assert question == "Hi"
    assert captured["url"] == "http://localhost:9999/v1/chat/completions"

@pytest.mark.asyncio
async def test_missing_local_llm_url_raises_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "local_llm_url", "")

    with pytest.raises(ValueError, match="local_llm_url must be configured"):
        await ai.generate_next_question(
            InterviewContext(job_description="Backend"),
            [],
        )


@pytest.mark.asyncio
async def test_http_error_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "local_llm_url", "http://localhost")

    async def fake_post(self, url, headers=None, json=None):
        return httpx.Response(
            400,
            text="bad request",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(RuntimeError, match="LLM provider request failed: 400"):
        await ai.generate_next_question(
            InterviewContext(job_description="Backend"),
            [],
        )
