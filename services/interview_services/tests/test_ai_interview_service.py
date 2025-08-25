import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx
import pytest

from interview_services import ai_interview_service as ai
from interview_services.schemas import InterviewContext, ConversationTurn
from interview_services.config import settings


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
async def test_determine_topics():
    topics = await ai.determine_topics(
        InterviewContext(
            job_description="Looking for Python developer",
            candidate_resume="Experience with databases",
        )
    )

    assert topics == ["python", "database"]


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
