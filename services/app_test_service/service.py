"""Testing helpers built on the default LLM gateway.

Includes utilities for:
- Generating a fake candidate profile for a job posting
- Generating an auto-answer to the latest interview question for a session
"""

from __future__ import annotations

import uuid
import json
from typing import Any, Dict, List, Optional

from gateway_service import gateway
from sample_data_service import sample_data_repo as samples
from session_service.database import get_session as db_get_session, get_conversation_turns as db_get_turns


async def generate_candidate_for_job(job_id: int) -> Dict[str, Any]:
    """Create a fake candidate profile and resume for the given job posting."""
    posting = samples.get_job_posting(job_id)
    if not posting:
        raise ValueError("Job not found")

    job_role = posting.get("job_title") or "Software Engineer"
    exp_level = posting.get("experience_level") or "Mid"
    years_map = {"junior": 2, "entry": 1, "mid": 5, "senior": 8, "lead": 10}
    years = years_map.get(str(exp_level).lower(), 5)

    profile_prompt = (
        "You are an expert tech career simulator. Your task is to generate a "
        "detailed, realistic, and \"spiky\" profile for a fictional tech job "
        "candidate based on a given role and experience level. The profile must be "
        "returned as a single, well-formed JSON object.\n\n"
        "**Instructions:**\n\n"
        "1.  **Generate a Profile:** Create a candidate profile based on the following input variables:\n"
        f"    * `job_role`: `{job_role}`\n"
        f"    * `experience_level`: `{exp_level}`\n"
        f"    * `years_of_experience`: `{years}`\n\n"
        "2.  **Ensure \"Spiky\" Skills:** The `skill_matrix` is the most important part. "
        "The proficiency scores MUST be intentionally uneven to reflect a real person's skillset.\n"
        "    * The candidate must have 2-3 clear \"spikes\" (skills with proficiency 9-10).\n"
        "    * The candidate must have at least one significant \"valley\" (a relevant skill with proficiency 1-3).\n"
        "    * Other skills should be distributed realistically across the \"Familiar\" and \"Proficient\" ranges.\n"
        "    * Use the following proficiency scale:\n"
        "        * 1-2: Beginner\n"
        "        * 3-5: Familiar\n"
        "        * 6-8: Proficient\n"
        "        * 9-10: Expert\n\n"
        "3.  **Link Snippets to Spikes:** The `project_snippets` must be directly linked to the candidate's highest-rated skills (their \"spikes\"). Each snippet should provide a narrative \"proof\" of their expertise in that area. The stories should be concise and written in the first person.\n\n"
        "4.  **JSON Output Only:** The final output MUST be a single, raw JSON object. Do not include any introductory text, explanations, markdown formatting like ```json, or anything else outside of the JSON structure.\n\n"
        "**JSON Schema:**\n\n"
        "{"
        "  \"core_identity\": {\n"
        "    \"name\": \"string (Generate a realistic name)\",\n"
        "    \"applying_for\": \"string (Use the provided job_role)\",\n"
        "    \"experience_level\": \"string (Use the provided experience_level)\",\n"
        "    \"years_of_experience\": \"integer (Use the provided years_of_experience)\"\n"
        "  },\n"
        "  \"skill_matrix\": [\n"
        "    {\n"
        "      \"skill\": \"string\",\n"
        "      \"category\": \"string (e.g., 'Languages', 'Frameworks', 'Databases', 'Tools/Infra', 'Concepts')\",\n"
        "      \"proficiency\": \"integer (1-10)\"\n"
        "    }\n"
        "  ],\n"
        "  \"project_snippets\": [\n"
        "    {\n"
        "      \"linked_skill\": \"string (The 'spike' skill this story relates to)\",\n"
        "      \"story\": \"string (A first-person project story using the STAR method implicitly)\"\n"
        "    }\n"
        "  ],\n"
        "  \"personality\": {\n"
        "    \"confidence\": \"string (e.g., 'High', 'Medium', 'Low')\",\n"
        "    \"verbosity\": \"string (e.g., 'Concise', 'Balanced', 'Verbose')\",\n"
        "    \"quirk\": \"string (A unique, subtle interview behavior)\"\n"
        "  }\n"
        "}"
    )

    profile_data = await gateway.execute_task(
        task_name="fake_candidate_profile",
        system_prompt=profile_prompt,
    )

    profile_json = ""
    if isinstance(profile_data, dict):
        try:
            profile_json = json.dumps(profile_data)
        except Exception:
            profile_json = json.dumps({})
    else:
        profile_json = str(profile_data)

    resume_prompt = (
        "Using the following candidate profile and job description, craft a concise "
        "resume paragraph summarizing the candidate's relevant experience. Respond "
        "ONLY with a JSON object containing a 'resume' field.\n\n"
        f"Candidate Profile:\n{profile_json}\n\n"
        f"Job Description:\n{posting['description']}"
    )

    resume_data = await gateway.execute_task(
        task_name="fake_candidate_resume",
        system_prompt=resume_prompt,
    )

    resume_text = ""
    if isinstance(resume_data, dict):
        resume_text = resume_data.get("resume") or resume_data.get("text") or ""
    else:
        resume_text = str(resume_data)

    candidate_id = str(uuid.uuid4())
    samples.upsert_candidate(candidate_id, job_id, profile_json, resume_text)
    # Maintain legacy resume table for compatibility
    samples.upsert_candidate_resume(candidate_id, resume_text, job_id)
    return {"candidate_id": candidate_id, "profile": json.loads(profile_json or "{}"), "resume": resume_text}


async def generate_auto_answer_for_session(
    session_id: str,
    correctness_level: float,
    confidence_level: float,
    *,
    # New optional controls
    confidence: Optional[str] = None,
    verbosity: Optional[str] = None,
    skill_matrix: Optional[Any] = None,
    # Context
    job_description: Optional[str] = None,
    candidate_resume: Optional[str] = None,
    candidate_profile: Optional[str] = None,
    candidate_id: Optional[str] = None,
    job_id: Optional[int] = None,
) -> Dict[str, str]:
    """Generate a candidate-style answer to the latest question in a session.

    Parameters
    ----------
    session_id: str
        The interview session identifier (used to pull history and last question).
    correctness_level: float
        Desired technical correctness level [0.0, 1.0]. (legacy)
    confidence_level: float
        Desired confidence/hedging in tone [0.0, 1.0]. (legacy)
    confidence: Optional[str]
        One of {'High','Medium','Low'} to control tone. Overrides numeric if provided.
    verbosity: Optional[str]
        One of {'Concise','Balanced','Verbose'} to control verbosity.
    skill_matrix: Optional[Any]
        A JSON-serializable list or string describing the candidate's skill matrix.
    job_description: Optional[str]
        Full job description text (optional; falls back to blueprint evidence).
    candidate_resume: Optional[str]
        Full resume text (optional; falls back to blueprint evidence).
    candidate_profile: Optional[str]
        Full candidate profile JSON (optional).
    candidate_id: Optional[str]
        Candidate identifier to link with session for analytics.
    job_id: Optional[int]
        Job posting identifier to link with session for analytics.
    """
    # Clamp the legacy levels to [0, 1]
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

    # System prompt: role-play constraints with new controls if provided
    tone_lines: List[str] = [
        "Behaviors (use these without stating them):",
    ]
    if confidence:
        tone_lines.append(f"- Confidence: {confidence}.")
    else:
        tone_lines.append(f"- Confidence Level (0-1): {conf_lvl:.2f}.")
    if verbosity:
        tone_lines.append(f"- Verbosity: {verbosity}.")
    tone_lines.append(f"- Technical Correctness Level (0-1): {c_lvl:.2f}.")

    system_prompt = (
        "You are role-playing as a job candidate in a technical interview.\n"
        "Your goal is to answer the interviewer's latest question as the candidate would.\n\n"
        + "\n".join(tone_lines) + "\n\n"
        "Guidance:\n"
        "- Higher correctness => more accurate, grounded, and technically precise content.\n"
        "- Lower correctness => introduce typical mistakes or gaps plausibly, never gibberish.\n"
        "- If confidence is Low, use cautious tone and hedges; if High, be assertive.\n"
        "- If verbosity is Concise, keep to 2-3 sentences; Balanced: 3-5; Verbose: 5-7.\n"
        "- Do NOT reveal or mention any numeric levels.\n\n"
        "Respond ONLY with a single, valid JSON object containing an 'answer_text' field."
    )

    # User prompt packs the specific question and context
    parts: List[str] = []
    parts.append(f"Latest Question:\n{last_q}")
    if rez_text:
        parts.append(f"Candidate Resume (context):\n{rez_text}")
    if candidate_profile:
        parts.append(f"Candidate Profile (context):\n{candidate_profile}")
    # Add skill matrix override explicitly if provided
    if skill_matrix is not None:
        try:
            sm_text = json.dumps(skill_matrix)
        except Exception:
            sm_text = str(skill_matrix)
        parts.append(f"Skill Matrix (override):\n{sm_text}")
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

    if candidate_id and job_id:
        try:
            samples.link_candidate_session(candidate_id, int(job_id), session_id)
        except Exception:
            pass

    return {"answer_text": answer or ""}
