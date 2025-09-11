"""DSPy programs for Stage-3 theory checks."""
from __future__ import annotations

from typing import Optional

import dspy
from pydantic import BaseModel

from gateway_service import gateway


class TheoryQuestionInput(BaseModel):
    """Parameters for generating a theory check question."""

    skill: str
    confidence: int


class TheoryQuestionOutput(BaseModel):
    """Generated question text."""

    question_text: str


class TheoryQuestionProgram(dspy.Module):
    """Generate a concept-first verification question."""

    system_prompt_template: str = (
        "You are verifying understanding of '{skill}'. Candidate self-rated "
        "confidence {confidence}/5. Ask one concise concept-first question. "
        'Respond with JSON {{"question_text": string}}.'
    )

    async def __call__(self, inp: TheoryQuestionInput) -> TheoryQuestionOutput:
        system_prompt = self.system_prompt_template.format(
            skill=inp.skill, confidence=inp.confidence
        )
        data = await gateway.execute_task(
            task_name="stage_3_question",
            system_prompt=system_prompt,
        )
        return TheoryQuestionOutput.model_validate(data)


class TheoryEvalInput(BaseModel):
    """User answer to a theory check question."""

    answer: str


class TheoryEvalOutput(BaseModel):
    """Evaluation result and rationale."""

    result: str
    rationale: Optional[str] = None


class TheoryEvalProgram(dspy.Module):
    """Evaluate a theory check answer."""

    system_prompt: str = (
        "Evaluate the answer for correctness and depth. "
        'Respond with JSON {"result": string, "rationale": string}.'
    )

    async def __call__(self, inp: TheoryEvalInput) -> TheoryEvalOutput:
        data = await gateway.execute_task(
            task_name="stage_3_eval",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return TheoryEvalOutput.model_validate(data)
