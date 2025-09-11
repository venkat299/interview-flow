"""Core AI interview utilities."""

from typing import Optional

from .schemas import (
    InterviewRequest,
    InterviewContext,
    InterviewBlueprintResponse,
    EvaluationRequest,
    EvaluationResponse,
    ContextPacket,
    VerificationResult,
)
from gateway_service import gateway
from interviewer_service.personas import PERSONA_PROMPTS
from interviewer_service import LLMInterviewer
from monitor_service import LLMMonitor
from scoring_service import ScoringEngine



async def generate_introductory_question() -> str:
    """Generate a welcoming introductory question."""

    system_prompt = (
        "You are an AI technical interviewer. Your first task is to ask the candidate to briefly introduce themselves. "
        "The question should be welcoming and encourage a concise response. "
        "Respond ONLY with a single, valid JSON object with a single key 'question_text'."
    )

    data = await gateway.execute_task(
        task_name="question_generation",
        system_prompt=system_prompt,
    )

    return data["question_text"]


async def generate_soft_skill_question(candidate_resume: str) -> str:
    """Generate a soft-skill question using the candidate's resume."""

    system_prompt = (
        "You are an AI technical interviewer. Based on the following resume, generate a soft-skill question that explores the "
        "candidate's teamwork, communication, or problem-solving skills. The question should be open-ended but encourage a "
        "brief response. Resume: "
        f"{candidate_resume}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
    )

    data = await gateway.execute_task(
        task_name="question_generation",
        system_prompt=system_prompt,
    )

    return data["question_text"]


async def generate_next_question(request: InterviewRequest) -> str:
    """Generate the next interview question using the AI Gateway."""
    persona_prompt = PERSONA_PROMPTS.get(request.persona, "")

    constraints = [
        f"Topic Focus: The question MUST be about '{request.current_topic}'.",
        (
            f"Difficulty Level: The question's complexity MUST match the target difficulty of {request.current_difficulty}/5."
        ),
        (
            "Context: The question should be a logical follow-up to the existing conversation history. Do not repeat previous questions."
        ),
    ]

    if request.current_difficulty <= 2:
        constraints.append("Brevity: The question must be concise and short.")
    else:
        constraints.append("Brevity: Keep the question focused and clear.")

    if request.current_difficulty == 1:
        constraints.append(
            "Question Type: Randomly choose one of the following formats: yes/no, multiple choice, or short-answer. "
            "Include a 'question_type' key indicating the chosen format."
        )

    if request.needs_hint:
        constraints.append("Provide a subtle hint to guide the candidate within the question.")

    numbered_constraints = "\n".join(
        f"{idx + 1}.  {text}" for idx, text in enumerate(constraints)
    )

    system_prompt = (
        f"{persona_prompt}\n\n"
        "Your Task: Act as an AI technical interviewer. Generate the next single question for the candidate.\n\n"
        f"Constraints:\n{numbered_constraints}\n\n"
        "Respond ONLY with a single, valid JSON object with a single key 'question_text'"
    )

    if request.current_difficulty == 1:
        system_prompt += " and an optional 'question_type' key."
    else:
        system_prompt += "."

    history_lines = [f"{turn.role}: {turn.message}" for turn in request.history]
    user_prompt = "\n".join(history_lines)

    data = await gateway.execute_task(
        task_name="question_generation",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    return data["question_text"]


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


async def evaluate_candidate_answer(
    request: EvaluationRequest,
) -> EvaluationResponse:
    """Evaluate a candidate's answer using the AI Gateway."""

    tb = request.topic_blueprint
    system_prompt = (
        "You are an impartial and expert technical evaluator. Your task is to analyze a candidate's answer and score it based on the provided topic blueprint.\n\n"
        "**Topic Blueprint:**\n"
        f"- Topic: `{tb.name}`\n"
        f"- Required Depth: `{tb.required_depth}`\n"
        f"- Resume Evidence: `{tb.resume_evidence}`\n\n"
        "**Interview Turn:**\n"
        f"- Question Asked: `{request.question}`\n"
        f"- Candidate's Answer: `{request.answer}`\n\n"
        "**Evaluation Tasks:**\n"
        "1.  Provide a `score` from 0-10 for the answer's technical accuracy, clarity, and depth.\n"
        "2.  Determine the `assessed_depth` demonstrated ('Fundamental', 'Intermediate', 'Advanced', 'Expert').\n"
        "3.  State your `llm_confidence` in this evaluation ('High', 'Medium', 'Low').\n"
        "4.  Write a concise `justification` for your score.\n"
        "5.  Based on the `resume_evidence`, determine if the candidate's answer seems truthful (`is_truthful`). If the resume claims expertise but the answer is basic, this should be `false`.\n\n"
        "Respond ONLY with a single, valid JSON object that strictly adheres to the 'EvaluationResponse' schema."
    )

    data = await gateway.execute_task(
        task_name="answer_evaluation",
        system_prompt=system_prompt,
    )

    return EvaluationResponse.model_validate(data)

_interviewer = LLMInterviewer()
_monitor = LLMMonitor()
_scoring = ScoringEngine()


def _decrement_time(packet: ContextPacket, minutes: int) -> None:
    """Reduce available interview time on the context packet."""

    remaining = packet.time_remaining_min or packet.duration_min
    packet.time_remaining_min = max(remaining - minutes, 0)


async def analyze_jd_resume(
    jd_text: str, resume_text: str, duration_min: int = 18
) -> ContextPacket:
    """Stage-0: Analyze job description and resume to build the context packet."""

    system_prompt = (
        "Read the job description and resume. Return JSON with the following keys: "
        "role_from_jd, jd_core_skills (list), resume_claims (list), "
        "overlap_skills (list), primary_overlap_focus."
    )
    user_prompt = f"Job description:\n{jd_text}\n\nResume:\n{resume_text}"

    data = await gateway.execute_task(
        task_name="stage_0_analysis",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    packet = ContextPacket(
        jd_text=jd_text,
        resume_text=resume_text,
        duration_min=duration_min,
        role_from_jd=data.get("role_from_jd"),
        jd_core_skills=data.get("jd_core_skills", []),
        resume_claims=data.get("resume_claims", []),
        overlap_skills=data.get("overlap_skills", []),
        primary_overlap_focus=data.get("primary_overlap_focus"),
    )
    packet.time_remaining_min = packet.duration_min
    return packet


async def warmup_overview(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[str]:
    """Stage-1: Ask for a project overview and record goal and constraints."""

    if answer is None:
        prompt = (
            "Give me a 60–90 sec overview of a project most relevant to "
            f"{packet.primary_overlap_focus}: goal, your role, key constraints."
        )
        _decrement_time(packet, 1)
        return prompt

    system_prompt = (
        "Extract the project goal and list of key constraints from the answer. "
        "Respond with JSON having 'goal' and 'constraints' (list)."
    )
    data = await gateway.execute_task(
        task_name="stage_1_parse",
        system_prompt=system_prompt,
        user_prompt=answer,
    )
    packet.project_context.goal = data.get("goal")
    packet.project_context.constraints = data.get("constraints", [])
    return None


async def warmup_constraint(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[str]:
    """Stage-1: Ask about hardest constraint and capture scale/latency info."""

    if answer is None:
        question = (
            "What was the hardest constraint (scale, latency/SLA, reliability, cost) "
            "and how did it shape your design?"
        )
        _decrement_time(packet, 1)
        return question

    system_prompt = (
        "Extract any scale, latency, or SLO details from the answer. "
        "Respond with JSON {\"scale_latency_slo\": string}."
    )
    data = await gateway.execute_task(
        task_name="stage_1_parse",
        system_prompt=system_prompt,
        user_prompt=answer,
    )
    packet.project_context.scale_latency_slo = data.get("scale_latency_slo")
    return None


async def evidence_skill_question(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[str]:
    """Stage-2: Gather concrete responsibilities and skill hooks."""

    skills = packet.overlap_skills or packet.jd_core_skills

    if answer is None:
        skill_list = ", ".join(skills)
        question = (
            "Name 2–3 components you directly built/owned. For each: purpose, "
            "main interfaces, and your exact contribution. For the following "
            f"skills, describe one task you completed and rate your confidence "
            f"1–5: {skill_list}."
        )
        _decrement_time(packet, 4)
        return question

    system_prompt = (
        "From the answer, extract:"
        " skill_hooks (list of 3-5 concise items to verify later),"
        " confidence_ratings (mapping skill->1-5),"
        " and notes (brief bullets)."
        " Respond with JSON containing these keys."
    )
    data = await gateway.execute_task(
        task_name="stage_2_parse",
        system_prompt=system_prompt,
        user_prompt=answer,
    )
    packet.skill_hooks = data.get("skill_hooks", [])
    packet.confidence_ratings.update(data.get("confidence_ratings", {}))
    packet.notes.extend(data.get("notes", []))
    return None


async def theory_check_question(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[str]:
    """Stage-3: Verify fundamentals for each skill hook."""

    skills = packet.skill_hooks or packet.jd_core_skills
    idx = len(packet.verifications)
    if idx >= len(skills):
        return None
    skill = skills[idx]

    if answer is None:
        confidence = packet.confidence_ratings.get(skill, 3)
        system_prompt = (
            f"You are verifying understanding of '{skill}'. Candidate self-rated "
            f"confidence {confidence}/5. Ask one concise concept-first question. "
            'Respond with JSON {"question_text": string}.'
        )
        data = await gateway.execute_task(
            task_name="stage_3_question",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return data.get("question_text")

    system_prompt = (
        "Evaluate the answer for correctness and depth. Respond with JSON "
        '{"result": string, "rationale": string}.'
    )
    data = await gateway.execute_task(
        task_name="stage_3_eval",
        system_prompt=system_prompt,
        user_prompt=answer,
    )
    packet.verifications.append(
        VerificationResult(
            skill=skill,
            result=data.get("result"),
            rationale=data.get("rationale"),
        )
    )
    return None


async def wrap_up(packet: ContextPacket, answer: Optional[str] = None) -> Optional[str]:
    """Stage-4: Conclude the interview and capture a summary."""

    if answer is None:
        question = "Any questions about the role, roadmap, or stack?"
        _decrement_time(packet, 1)
        return question

    system_prompt = (
        "Using the prior notes and verification results, produce a brief "
        "internal summary with keys strengths, risks, follow_ups. Respond in "
        "JSON."
    )
    notes_blob = "; ".join(packet.notes)
    verif_blob = "; ".join(
        f"{v.skill}:{v.result}" for v in packet.verifications
    )
    user_prompt = f"Notes: {notes_blob}\nVerifications: {verif_blob}"
    data = await gateway.execute_task(
        task_name="stage_4_summary",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    strengths = data.get("strengths", [])
    risks = data.get("risks", [])
    follow_ups = data.get("follow_ups", [])
    if strengths:
        packet.notes.append("Strengths: " + ", ".join(strengths))
    if risks:
        packet.notes.append("Risks: " + ", ".join(risks))
    if follow_ups:
        packet.notes.append("Follow-ups: " + ", ".join(follow_ups))
    packet.time_remaining_min = 0
    return None


async def on_question_selected(question: str, state: dict | None = None) -> dict:
    """Hook invoked after the orchestrator selects a question.

    Parameters
    ----------
    question: str
        Raw question text selected by the orchestrator.
    state: dict | None
        Optional interview state for context.
    Returns
    -------
    dict
        Paraphrased question and monitor diagnostics.
    """
    paraphrased = await _interviewer.next_question(state or {}, {"stem": question})
    diag = await _monitor.assess_turn(state or {}, question, "")
    return {"question_text": paraphrased, "monitor": diag}


async def on_answer_scored(question: str, answer: str, state: dict | None = None) -> dict:
    """Hook invoked after an answer is evaluated.

    Parameters
    ----------
    question: str
        The question that was asked.
    answer: str
        Candidate's response.
    state: dict | None
        Interview state for reference.
    Returns
    -------
    dict
        Aggregated scoring payload.
    """
    diag = await _monitor.assess_turn(state or {}, question, answer)
    score = _scoring.aggregate(diag, [], {})
    return {"monitor": diag, "score": score}
