"""Core AI interview utilities."""

from .schemas import (
    InterviewRequest,
    InterviewContext,
    InterviewBlueprintResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from .ai_gateway import gateway
from .personas import PERSONA_PROMPTS


async def generate_next_question(request: InterviewRequest) -> str:
    """Generate the next interview question using the AI Gateway."""

    persona_prompt = PERSONA_PROMPTS.get(request.persona, "")
    system_prompt = (
        f"{persona_prompt}\n\n"
        "**Your Task:** Act as an AI technical interviewer. Generate the *next single question* for the candidate.\n\n"
        "**Constraints:**\n"
        f"1.  **Topic Focus:** The question MUST be about **'{request.current_topic}'**. Do not deviate.\n"
        f"2.  **Difficulty Level:** The question's complexity MUST match the target difficulty of **{request.current_difficulty}/5**. (1=Introductory, 5=Expert).\n"
        "3.  **Context:** The question should be a logical follow-up to the existing conversation history. Do not repeat previous questions.\n"
        "4.  **Brevity:** The question must be a single, concise question.\n\n"
        'Respond ONLY with a single, valid JSON object with a single key "question_text".'
    )

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
