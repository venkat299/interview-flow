"""Generate fake candidates for testing via the default LLM."""

from __future__ import annotations

import uuid
from typing import Dict

from gateway_service import gateway
from sample_data_service import sample_data_repo as samples


async def generate_candidate_for_job(job_id: int) -> Dict[str, str]:
    """Create a fake candidate resume for the given job posting.

    Uses the default LLM via the gateway to craft a realistic resume based
    on the job description. The generated resume is stored in the
    `candidate_resumes` table and returned to the caller.
    """
    posting = samples.get_job_posting(job_id)
    if not posting:
        raise ValueError("Job not found")

    system_prompt = (
        "You are to invent a realistic job candidate. Given the following job "
        "posting, craft a concise resume paragraph summarizing the candidate's "
        "relevant experience. Respond ONLY with a JSON object containing a "
        "'resume' field.\n\n"
        f"Job Title: {posting['job_title']}\n"
        f"Description: {posting['description']}"
    )

    data = await gateway.execute_task(
        task_name="fake_candidate_resume",
        system_prompt=system_prompt,
    )

    resume_text = data.get("resume") or data.get("text") or ""
    candidate_id = str(uuid.uuid4())
    samples.upsert_candidate_resume(candidate_id, resume_text, job_id)
    return {"candidate_id": candidate_id, "resume": resume_text}
