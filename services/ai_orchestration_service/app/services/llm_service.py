"""Service for interacting with various LLM providers."""

from typing import List

import httpx

from core.config import settings
from schemas.interview import ConversationTurn, InterviewContext


async def generate_next_question(
    context: InterviewContext, history: List[ConversationTurn]
) -> str:
    """Generate the next interview question using the configured LLM."""

    system_prompt = (
        "You are an AI technical interviewer. "
        f"The job description is: {context.job_description}. "
        "Ask the candidate the next question based on the conversation so far."
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
        payload = {"model": "google/gemma-3-1b", "messages": messages, "stream": False}
        headers = {"Content-Type": "application/json"}
        url = settings.local_llm_url
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()

