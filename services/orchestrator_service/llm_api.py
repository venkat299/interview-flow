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
from common.skill_inventory import SKILL_INVENTORY
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
from .followups import update_followup_hooks



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
_theory_question = TheoryQuestionProgram()
_theory_eval = TheoryEvalProgram()
_wrap_up = WrapUpProgram()
_graph = build_interview_graph()


def _decrement_time(packet: ContextPacket, minutes: int) -> None:
    """Reduce available interview time on the context packet."""

    remaining = packet.time_remaining_min or packet.duration_min
    packet.time_remaining_min = max(remaining - minutes, 0)


def _skill_prompt_context(packet: ContextPacket) -> str:
    """Build a concise phrase referencing role skills and hooks."""

    tags = ", ".join(packet.role_skill_tags[:5])
    hooks = ", ".join(packet.skill_hooks[:3])
    followups = ", ".join(packet.followup_hooks[:3])
    parts = []
    if tags:
        parts.append(f"technologies like {tags}")
    if hooks:
        parts.append(f"constraints such as {hooks}")
    if followups:
        parts.append(f"topics such as {followups}")
    return (" involving " + " and ".join(parts)) if parts else ""


async def analyze_jd_resume(
    jd_text: str, resume_text: str, duration_min: int = 18
) -> ContextPacket:
    """Stage-0: Analyze job description and resume to build the context packet."""

    out = await _stage0(
        JDResumeAnalysisInput(jd_text=jd_text, resume_text=resume_text)
    )

    canonical_tags = SKILL_INVENTORY.get(out.role_from_jd or "", [])
    data = await gateway.execute_task(
        task_name="skill_tag_refinement",
        system_prompt=(
            "Expand the provided canonical skill tags with additional related tags found in the job description and resume. "
            "Respond with JSON {\"tags\": [string]}"
        ),
        user_prompt=(
            f"Role: {out.role_from_jd}\n"
            f"Canonical tags: {canonical_tags}\n"
            f"Job description: {jd_text}\n"
            f"Resume: {resume_text}"
        ),
    )
    expanded_tags = data.get("tags", [])
    merged_tags = list(dict.fromkeys(list(canonical_tags) + list(expanded_tags)))

    packet = ContextPacket(
        jd_text=jd_text,
        resume_text=resume_text,
        duration_min=duration_min,
        role_from_jd=out.role_from_jd,
        jd_core_skills=out.jd_core_skills,
        resume_claims=out.resume_claims,
        overlap_skills=out.overlap_skills,
        primary_overlap_focus=out.primary_overlap_focus,
        role_skill_tags=merged_tags,
    )
    packet.time_remaining_min = packet.duration_min
    return packet


async def warmup_select_project(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: have the candidate pick a project."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate to name the project from their resume that is most relevant to "
            f"{packet.primary_overlap_focus}. The question should be concise and request only the project name. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_project"}

    data = await gateway.execute_task(
        task_name="stage_1_parse",
        system_prompt='Extract the project name. Respond with JSON {"project_name": string}.',
        user_prompt=answer,
    )
    packet.selected_project = data.get("project_name")
    update_followup_hooks(packet, answer)
    return None


async def warmup_role_context(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: capture role and team size."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate, in one concise sentence, to state their role and team size on the project "
            f"{packet.selected_project}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_role"}

    data = await WarmupRoleProgram()(WarmupRoleInput(answer=answer))
    packet.project_context.role = data.role
    packet.project_context.team_size = data.team_size
    update_followup_hooks(packet, answer)
    return None


async def warmup_architecture(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: high-level architecture and technologies."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate to briefly describe the high-level architecture and key technologies of their project "
            f"{packet.selected_project} in one sentence. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_architecture"}

    data = await WarmupArchitectureProgram()(WarmupArchitectureInput(answer=answer))
    packet.project_context.architecture = data.architecture
    packet.project_context.key_technologies = data.key_technologies
    packet.project_context.followup_hooks = data.followup_hooks
    packet.followup_hooks.extend(h for h in data.followup_hooks if h not in packet.followup_hooks)
    update_followup_hooks(packet, answer)
    return None


async def warmup_constraints(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: capture key constraints."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate to list the main technical constraints they faced on the project "
            f"{packet.selected_project} (for example, scale or latency). Keep the question short. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_constraints"}

    data = await WarmupConstraintsProgram()(WarmupConstraintsInput(answer=answer))
    packet.project_context.constraints = data.constraints
    update_followup_hooks(packet, answer)
    return None


async def warmup_challenge(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: hardest challenge faced."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate to describe, in one sentence, the toughest technical challenge they faced on the project "
            f"{packet.selected_project} and how they addressed it. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_challenge"}

    data = await WarmupChallengeProgram()(WarmupChallengeInput(answer=answer))
    packet.project_context.hardest_challenge = data.hardest_challenge
    update_followup_hooks(packet, answer)
    return None


async def warmup_outcome(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: outcomes or metrics achieved."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate, in one sentence, about a measurable outcome or metric achieved by the project "
            f"{packet.selected_project}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_outcome"}

    data = await WarmupOutcomeProgram()(WarmupOutcomeInput(answer=answer))
    packet.project_context.outcomes = data.outcomes
    packet.project_context.evaluation_metrics = data.evaluation_metrics
    update_followup_hooks(packet, answer)
    return None


async def warmup_reflection(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Warm-up step: reflection or lessons learned."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer. Ask the candidate to reflect on the project "
            f"{packet.selected_project} and state, in one sentence, what they would improve or do differently. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "warmup_reflection"}

    data = await WarmupReflectionProgram()(WarmupReflectionInput(answer=answer))
    packet.project_context.lessons = data.lessons
    update_followup_hooks(packet, answer)
    return None


async def evidence_components(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-2 step: ask about project components owned."""

    if answer is None:
        context = _skill_prompt_context(packet)
        system_prompt = (
            "You are an AI technical interviewer asking the candidate to briefly list 2–3 major components they built on the selected project, noting each component's purpose and main interfaces"
            f"{context}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 2)
        return {"question_text": data["question_text"], "question_type": "evidence_components"}

    packet.notes.append(f"Components: {answer}")
    update_followup_hooks(packet, answer)
    return None


async def evidence_choice_space(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-2 step: ask about considered options or approaches."""

    if answer is None:
        context = _skill_prompt_context(packet)
        system_prompt = (
            "You are an AI technical interviewer asking, in one short question, what options or approaches the candidate considered for the chosen project"
            f"{context}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "evidence_choice_space"}

    data = await gateway.execute_task(
        task_name="stage_2_parse",
        system_prompt='Extract the options or approaches mentioned as short notes. Respond with JSON {"notes": [string]}.' ,
        user_prompt=answer,
    )
    packet.notes.extend([f"Choice space: {n}" for n in data.get("notes", [])])
    update_followup_hooks(packet, answer)
    return None


async def evidence_decision_rationale(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-2 step: probe why a specific option was chosen."""

    if answer is None:
        context = _skill_prompt_context(packet)
        system_prompt = (
            "You are an AI technical interviewer asking the candidate to briefly explain why they chose a particular option from the ones considered"
            f"{context}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "evidence_decision_rationale"}

    data = await gateway.execute_task(
        task_name="stage_2_parse",
        system_prompt='Summarize the candidate\'s rationale in under 10 words. Respond with JSON {"notes": [string]}.' ,
        user_prompt=answer,
    )
    packet.notes.extend([f"Rationale: {n}" for n in data.get("notes", [])])
    update_followup_hooks(packet, answer)
    return None


async def evidence_outcome_validation(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-2 step: request evidence that the choice worked."""

    if answer is None:
        context = _skill_prompt_context(packet)
        system_prompt = (
            "You are an AI technical interviewer; in a short question, ask the candidate for brief evidence that their chosen option succeeded"
            f"{context}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "evidence_outcome_validation"}

    data = await gateway.execute_task(
        task_name="stage_2_parse",
        system_prompt='List the pieces of evidence that the choice worked. Respond with JSON {"notes": [string]}.' ,
        user_prompt=answer,
    )
    packet.notes.extend([f"Outcome: {n}" for n in data.get("notes", [])])
    update_followup_hooks(packet, answer)
    return None


async def evidence_tradeoff_reflection(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-2 step: explore trade-offs or alternative paths."""

    if answer is None:
        context = _skill_prompt_context(packet)
        system_prompt = (
            "You are an AI technical interviewer asking the candidate to reflect on trade-offs or alternative paths they considered and why those were not chosen"
            f"{context}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "evidence_tradeoff_reflection"}

    data = await gateway.execute_task(
        task_name="stage_2_parse",
        system_prompt='Summarize the trade-offs or alternatives mentioned. Respond with JSON {"notes": [string]}.' ,
        user_prompt=answer,
    )
    packet.notes.extend([f"Trade-offs: {n}" for n in data.get("notes", [])])
    update_followup_hooks(packet, answer)
    return None


async def theory_primary_question(
    packet: ContextPacket, skill: str, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-3 step: ask a primary theory question for a skill."""

    if answer is None:
        q_out = await _theory_question(TheoryQuestionInput(skill=skill))
        _decrement_time(packet, 1)
        return {"question_text": q_out.question_text, "question_type": "theory_primary"}

    e_out = await _theory_eval(TheoryEvalInput(answer=answer))
    packet.verifications.append(
        VerificationResult(skill=skill, result=e_out.result, rationale=e_out.rationale)
    )
    return None


async def theory_followup_question(
    packet: ContextPacket, skill: str, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-3 step: follow-up question on the same skill.

    The difficulty of the follow-up is based on the prior verification result.
    """

    if answer is None:
        last = next(
            (v for v in reversed(packet.verifications) if v.skill == skill),
            None,
        )
        if last and last.result == "pass":
            system_prompt = (
                f"You are verifying advanced understanding of '{skill}'. "
                "Ask a harder follow-up question. Respond with JSON {\"question_text\": string}."
            )
        else:
            rationale = last.rationale if last else ""
            system_prompt = (
                f"You are verifying understanding of '{skill}'. The candidate's previous answer was incorrect. "
                f"Reference: {rationale}. Ask a follow-up question to address the misunderstanding. "
                "Respond with JSON {\"question_text\": string}."
            )
        data = await gateway.execute_task(
            task_name="stage_3_question",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "theory_followup"}

    e_out = await _theory_eval(TheoryEvalInput(answer=answer))
    if packet.verifications:
        packet.verifications[-1].followup_result = e_out.result
        packet.verifications[-1].followup_rationale = e_out.rationale
    return None


async def wrapup_candidate_questions(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-4 step: invite candidate questions about the role or team."""

    if answer is None:
        notes = "; ".join(packet.notes)
        system_prompt = (
            "You are an AI technical interviewer wrapping up the conversation. Based on these notes from the interview, ask the candidate in one short sentence if they have any questions about the role, team, or company. "
            f"Notes: {notes}. Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "wrapup_candidate_questions"}

    packet.notes.append(f"Candidate questions: {answer}")
    return None


async def wrapup_feedback(
    packet: ContextPacket, answer: Optional[str] = None
) -> Optional[dict]:
    """Stage-4 step: gather feedback and finalize summary."""

    if answer is None:
        system_prompt = (
            "You are an AI technical interviewer concluding the interview. Ask the candidate for brief feedback on this interview experience. "
            "Respond ONLY with a single, valid JSON object with a single key 'question_text'."
        )
        data = await gateway.execute_task(
            task_name="question_generation",
            system_prompt=system_prompt,
        )
        _decrement_time(packet, 1)
        return {"question_text": data["question_text"], "question_type": "wrapup_feedback"}

    packet.notes.append(f"Candidate feedback: {answer}")
    out = await _wrap_up(WrapUpInput(notes=packet.notes, verifications=packet.verifications))
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
