"""Testing helpers built on the default LLM gateway.

Includes utilities for:
- Generating a fake candidate profile for a job posting
- Generating an auto-answer to the latest interview question for a session
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from gateway_service import gateway
from sample_data_service import sample_data_repo as samples
from session_service.database import get_session as db_get_session, get_conversation_turns as db_get_turns


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


async def generate_auto_answer_for_session(
    session_id: str,
    correctness_level: float,
    confidence_level: float,
    *,
    job_description: Optional[str] = None,
    candidate_resume: Optional[str] = None,
) -> Dict[str, str]:
    """Generate a candidate-style answer to the latest question in a session.

    Parameters
    ----------
    session_id: str
        The interview session identifier (used to pull history and last question).
    correctness_level: float
        Desired technical correctness level [0.0, 1.0].
    confidence_level: float
        Desired confidence/hedging in tone [0.0, 1.0].
    job_description: Optional[str]
        Full job description text (optional; falls back to blueprint evidence).
    candidate_resume: Optional[str]
        Full resume text (optional; falls back to blueprint evidence).
    """
    # Clamp the levels to [0, 1]
    try:
        c_lvl = max(0.0, min(1.0, float(correctness_level)))
    except Exception:
        c_lvl = 0.8
    try:
        conf_lvl = max(0.0, min(1.0, float(confidence_level)))
    except Exception:
        conf_lvl = 0.7

    sess = db_get_session(session_id)
    if not sess:
        raise ValueError("Session not found")

    turns = db_get_turns(session_id) or []
    # Find the last interviewer question
    last_q = ""
    for t in reversed(turns):
        if str(t.get("role")).lower() == "interviewer":
            last_q = t.get("message") or ""
            break
    if not last_q:
        raise ValueError("No interviewer question found for this session")

    # Build brief history lines (limit to last ~10 turns to keep prompts small)
    def _fmt_turn(t: Dict) -> str:
        role = str(t.get("role") or "").strip()
        msg = str(t.get("message") or "").strip()
        if not role or not msg:
            return ""
        if role.lower() == "interviewer":
            return f"Interviewer: {msg}"
        if role.lower() == "candidate":
            return f"Candidate: {msg}"
        return f"{role}: {msg}"

    history_lines: List[str] = [_fmt_turn(t) for t in turns[-10:]]
    history_text = "\n".join([h for h in history_lines if h])

    # Use blueprint-evidence as a fallback context if full texts not provided
    blueprint = sess.get("blueprint") or {}
    topics = blueprint.get("topics") or []
    jd_points: List[str] = []
    resume_points: List[str] = []
    for tp in topics:
        jd_points.extend([str(x) for x in (tp.get("jd_context") or [])])
        resume_points.extend([str(x) for x in (tp.get("resume_evidence") or [])])

    jd_text = (job_description or "").strip()
    rez_text = (candidate_resume or "").strip()
    if not jd_text and jd_points:
        jd_text = "\n".join(f"- {p}" for p in jd_points[:12])
    if not rez_text and resume_points:
        rez_text = "\n".join(f"- {p}" for p in resume_points[:12])

    # System prompt: role-play constraints and levels
    system_prompt = (
        "You are role-playing as a job candidate in a technical interview.\n"
        "Your goal is to answer the interviewer's latest question as the candidate would.\n\n"
        "Behaviors (use these levels without mentioning them):\n"
        f"- Technical Correctness Level (0-1): {c_lvl:.2f}.\n"
        f"- Confidence Level (0-1): {conf_lvl:.2f}.\n\n"
        "Guidance:\n"
        "- Higher correctness => more accurate, grounded, and technically precise content.\n"
        "- Lower correctness => introduce typical mistakes or gaps plausibly, not nonsense.\n"
        "- Higher confidence => assertive tone, fewer hedges.\n"
        "- Lower confidence => hedging, uncertainty markers, cautious tone.\n"
        "- Keep the answer concise (2-6 sentences).\n"
        "- Do NOT reveal or mention any numeric levels.\n\n"
        "Respond ONLY with a single, valid JSON object containing an 'answer_text' field."
    )

    # User prompt packs the specific question and context
    parts: List[str] = []
    parts.append(f"Latest Question:\n{last_q}")
    if rez_text:
        parts.append(f"Candidate Resume (context):\n{rez_text}")
    if jd_text:
        parts.append(f"Job Description / Responsibilities (context):\n{jd_text}")
    if history_text:
        parts.append(f"Recent Chat History:\n{history_text}")
    user_prompt = "\n\n".join(parts)

    # Route via the gateway. We ask for JSON; if the provider returns text,
    # use the question_generation task for a robust fallback to plain text.
    data = await gateway.execute_task(
        task_name="question_generation",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    # Best-effort extraction of the answer text
    answer = ""
    if isinstance(data, dict):
        for k in ("answer_text", "answer", "text", "content", "question_text"):
            if isinstance(data.get(k), str) and data.get(k).strip():
                answer = data.get(k).strip()
                break
    if not answer:
        # Fallback to string repr if any
        try:
            answer = str(data).strip()
        except Exception:
            answer = ""

    return {"answer_text": answer or ""}
