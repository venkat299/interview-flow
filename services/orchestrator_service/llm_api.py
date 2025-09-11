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
from .programs.stage0_analysis import (
    Stage0AnalysisProgram,
    JDResumeAnalysisInput,
)
from .programs.stage1_warmup import (
    WarmupRoleProgram,
    WarmupRoleInput,
    WarmupArchitectureProgram,
    WarmupArchitectureInput,
    WarmupConstraintsProgram,
    WarmupConstraintsInput,
    WarmupChallengeProgram,
    WarmupChallengeInput,
    WarmupOutcomeProgram,
    WarmupOutcomeInput,
    WarmupReflectionProgram,
    WarmupReflectionInput,
)
from .programs.stage2_evidence import (
    EvidenceProgram,
    EvidenceInput,
)
from .programs.stage3_theory import (
    TheoryQuestionProgram,
    TheoryQuestionInput,
    TheoryEvalProgram,
    TheoryEvalInput,
)
from .programs.stage4_wrapup import (
    WrapUpProgram,
    WrapUpInput,
)
from .flow import build_interview_graph



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
_stage0 = Stage0AnalysisProgram()
_evidence = EvidenceProgram()
_theory_question = TheoryQuestionProgram()
_theory_eval = TheoryEvalProgram()
_wrap_up = WrapUpProgram()
_graph = build_interview_graph()


def _decrement_time(packet: ContextPacket, minutes: int) -> None:
    """Reduce available interview time on the context packet."""

    remaining = packet.time_remaining_min or packet.duration_min
    packet.time_remaining_min = max(remaining - minutes, 0)


async def analyze_jd_resume(
    jd_text: str, resume_text: str, duration_min: int = 18
) -> ContextPacket:
    """Stage-0: Analyze job description and resume to build the context packet."""

    out = await _stage0(
        JDResumeAnalysisInput(jd_text=jd_text, resume_text=resume_text)
    )

    packet = ContextPacket(
        jd_text=jd_text,
        resume_text=resume_text,
        duration_min=duration_min,
        role_from_jd=out.role_from_jd,
        jd_core_skills=out.jd_core_skills,
        resume_claims=out.resume_claims,
        overlap_skills=out.overlap_skills,
        primary_overlap_focus=out.primary_overlap_focus,
    )
    packet.time_remaining_min = packet.duration_min
    return packet


async def warmup_select_project(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: have the candidate pick a project."""

    if answer is None:
        question = (
            "Name the project most relevant to "
            f"{packet.primary_overlap_focus}. Reply with the project name only."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_project"}

    data = await gateway.execute_task(
        task_name="stage_1_parse",
        system_prompt='Extract the project name. Respond with JSON {"project_name": string}.',
        user_prompt=answer,
    )
    packet.selected_project = data.get("project_name")
    return None


async def warmup_role_context(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: capture role and team size."""

    if answer is None:
        question = (
            f"In one sentence, what was your role and team size on {packet.selected_project}? "
            "Be concise."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_role"}

    data = await WarmupRoleProgram()(WarmupRoleInput(answer=answer))
    packet.project_context.role = data.role
    packet.project_context.team_size = data.team_size
    return None


async def warmup_architecture(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: high-level architecture and technologies."""

    if answer is None:
        question = (
            "Briefly describe the high-level architecture and key technologies. "
            "Answer in one sentence."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_architecture"}

    data = await WarmupArchitectureProgram()(WarmupArchitectureInput(answer=answer))
    packet.project_context.architecture = data.architecture
    packet.project_context.key_technologies = data.key_technologies
    return None


async def warmup_constraints(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: capture key constraints."""

    if answer is None:
        question = (
            "List the main technical constraints you faced (e.g., scale, latency). "
            "Keep it short."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_constraints"}

    data = await WarmupConstraintsProgram()(WarmupConstraintsInput(answer=answer))
    packet.project_context.constraints = data.constraints
    return None


async def warmup_challenge(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: hardest challenge faced."""

    if answer is None:
        question = (
            "What was the toughest technical challenge and how did you address it? One sentence."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_challenge"}

    data = await WarmupChallengeProgram()(WarmupChallengeInput(answer=answer))
    packet.project_context.hardest_challenge = data.hardest_challenge
    return None


async def warmup_outcome(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: outcomes or metrics achieved."""

    if answer is None:
        question = (
            "What measurable outcome or metric did the project achieve? One sentence."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_outcome"}

    data = await WarmupOutcomeProgram()(WarmupOutcomeInput(answer=answer))
    packet.project_context.outcomes = data.outcomes
    return None


async def warmup_reflection(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: reflection or lessons learned."""

    if answer is None:
        question = (
            "Looking back, what would you improve or do differently? One sentence."
        )
        _decrement_time(packet, 1)
        return {"question_text": question, "question_type": "warmup_reflection"}

    data = await WarmupReflectionProgram()(WarmupReflectionInput(answer=answer))
    packet.project_context.lessons = data.lessons
    return None


async def evidence_skill_question(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[str]:
    """Stage-2: Gather concrete responsibilities and skill hooks."""

    skills = packet.overlap_skills or packet.jd_core_skills

    if answer is None:
        skill_list = ", ".join(skills)
        system_prompt = (
            "You are an AI technical interviewer. Generate a question asking the candidate to name 2–3 components they directly built or owned, "
            "including each component's purpose, main interfaces, and their exact contribution. Also ask them to describe one task completed and rate their confidence 1–5 for each of the following skills: "
            f"{skill_list}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 4)
        return data["question_text"]

    out = await _evidence(EvidenceInput(answer=answer))
    packet.skill_hooks = out.skill_hooks
    packet.confidence_ratings.update(out.confidence_ratings)
    packet.notes.extend(out.notes)
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
        q_out = await _theory_question(
            TheoryQuestionInput(skill=skill, confidence=confidence)
        )
        _decrement_time(packet, 1)
        return q_out.question_text

    e_out = await _theory_eval(TheoryEvalInput(answer=answer))
    packet.verifications.append(
        VerificationResult(
            skill=skill,
            result=e_out.result,
            rationale=e_out.rationale,
        )
    )
    return None


async def wrap_up(packet: ContextPacket, answer: Optional[str] = None) -> Optional[str]:
    """Stage-4: Conclude the interview and capture a summary."""

    if answer is None:
        notes = "; ".join(packet.notes)
        system_prompt = (
            "You are an AI technical interviewer wrapping up the conversation. Based on these notes from the interview, generate a final personalized question inviting the candidate to ask about the role, roadmap, stack, or anything else. "
            f"Notes: {notes}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return data["question_text"]

    out = await _wrap_up(
        WrapUpInput(notes=packet.notes, verifications=packet.verifications)
    )
    if out.strengths:
        packet.notes.append("Strengths: " + ", ".join(out.strengths))
    if out.risks:
        packet.notes.append("Risks: " + ", ".join(out.risks))
    if out.follow_ups:
        packet.notes.append("Follow-ups: " + ", ".join(out.follow_ups))
    packet.time_remaining_min = 0
    return None


async def run_interview(packet: ContextPacket) -> ContextPacket:
    """Execute the full LangGraph interview flow starting from ``packet``."""
    result = await _graph.ainvoke(packet)
    return ContextPacket.model_validate(result)


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
