"""Core AI interview utilities."""
from typing import List

import httpx

from .config import settings
from .schemas import ConversationTurn, InterviewContext


async def generate_next_question(
    context: InterviewContext, history: List[ConversationTurn]
) -> str:
    """Generate the next interview question using the configured LLM."""

    system_prompt = (
        "You are an AI technical interviewer. "
        f"The job description is: {context.job_description}. "
        "Ask the candidate the next question based on the conversation so far. Your question should be concise"
    )

    provider = settings.llm_provider.lower()

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        role = "user" if turn.role == "candidate" else "assistant"
        messages.append({"role": role, "content": turn.message})

    if provider == "openai":
        payload = {"model": settings.openai_model, "messages": messages}
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        url = "https://api.openai.com/v1/chat/completions"
    elif provider == "local":
        payload = {"model": "openai/gpt-oss-20b", "messages": messages, "stream": False}
        headers = {"Content-Type": "application/json"}
        url = settings.local_llm_url
        if not url:
            raise ValueError("local_llm_url must be configured for local LLM provider")
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RuntimeError(
                f"LLM provider request failed: {exc.response.status_code} {detail}"
            ) from exc
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def determine_topics(context: InterviewContext) -> List[str]:
    """Infer interview topics from job description and resume."""

    text = f"{context.job_description} {context.candidate_resume or ''}".lower()
    keywords = ["python", "javascript", "java", "frontend", "backend", "database", "data science", "machine learning"]
    topics = [word for word in keywords if word in text]
    return topics or ["general"]
