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

    # Build a plain-text conversation for providers that require it
    conversation_text = "".join(
        f"{turn.role}: {turn.message}\n" for turn in history
    )
    prompt_text = f"{system_prompt}\n{conversation_text}".strip()

    provider = "local" # settings.llm_provider.lower()

    if provider == "openai":
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            messages.append({"role": turn.role, "content": turn.message})

        payload = {"model": settings.openai_model, "messages": messages}
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    if provider == "gemini":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-pro:generateContent"
            f"?key={settings.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return (
            data["candidates"][0]["content"]["parts"][0]["text"].strip()
        )

    if provider == "local":
        # The payload now matches the structure from the curl command
        payload = {
            "context": context.dict(),
            "history": [turn.dict() for turn in history]
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            # The URL is now taken from settings, which you should update
            response = await client.post(settings.local_llm_url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        # Assuming the local server returns an OpenAI-compatible response
        return data["choices"][0]["message"]["content"].strip()

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")