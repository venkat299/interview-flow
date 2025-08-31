"""Core AI interview utilities."""
from typing import List

import httpx

from .config import settings
from .schemas import (
    ConversationTurn,
    InterviewContext,
    InterviewBlueprintResponse,
)
from .ai_gateway import gateway


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
        payload = {"model": settings.local_model, "messages": messages, "stream": False}
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


async def create_interview_blueprint(context: InterviewContext) -> InterviewBlueprintResponse:
    """Generate a structured interview blueprint via the AI Gateway."""

    system_prompt = (
        "You are a world-class technical architect and hiring manager. "
        "Your task is to analyze a job description and a candidate's resume "
        "to create a comprehensive 'Interview Blueprint'. Your analysis must be "
        "objective and strictly based on the provided texts.\n\n"
        "Perform the following actions:\n"
        "1.  Infer a suitable `interview_title` for this role.\n"
        "2.  Infer the candidate's `experience_level` based on their resume (e.g., 'Junior', 'Mid-Level', 'Senior').\n"
        "3.  Identify the 5-7 most critical technical `topics`. For each topic:\n"
        "    a.  Assign a `relevance_to_role` score (0-10) based only on the job description.\n"
        "    b.  Determine the `required_depth` ('Fundamental', 'Intermediate', 'Advanced', 'Expert') based on the job's seniority.\n"
        "    c.  Extract verbatim `jd_context` phrases that justify the topic's inclusion and relevance.\n"
        "    d.  Extract verbatim `resume_evidence` phrases that suggest the candidate's proficiency.\n\n"
        "Respond ONLY with a single, valid JSON object that strictly adheres to the 'InterviewBlueprintResponse' schema."
    )
    user_prompt = (
        f"Job description:\n{context.job_description}\n\n"
        f"Candidate resume:\n{context.candidate_resume or ''}"
    )

    data = await gateway.execute_task(
        task_name="blueprint_generation",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    return InterviewBlueprintResponse.model_validate(data)
