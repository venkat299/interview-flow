"""DSPy program for Stage-1 introductory greeting."""
from __future__ import annotations

import dspy
from pydantic import BaseModel, Field

from gateway_service import gateway


class IntroModuleInput(BaseModel):
    """Inputs for tailoring the introductory greeting."""

    role: str | None = Field(default=None, description="Role title inferred from the JD")
    candidate_name: str | None = Field(
        default=None, description="Optional candidate name for personalization"
    )


class IntroModuleOutput(BaseModel):
    """Generated introductory question."""

    question_text: str = Field(..., description="The greeting and introduction request")


class Stage1IntroProgram(dspy.Module):
    """Generate a warm greeting that requests a brief introduction."""

    system_prompt_template: str = (
        "You are the AI interviewer for a {role} hiring conversation. "
        "Greet the {candidate} warmly and invite them to briefly tell you about themselves. "
        "Keep the prompt concise and welcoming. Respond with JSON {{\"question_text\": string}}."
    )

    async def __call__(self, inp: IntroModuleInput) -> IntroModuleOutput:
        role = inp.role or "open position"
        candidate = inp.candidate_name or "candidate"
        system_prompt = self.system_prompt_template.format(role=role, candidate=candidate)
        data = await gateway.execute_task(
            task_name="stage_1_intro",
            system_prompt=system_prompt,
        )
        return IntroModuleOutput.model_validate(data)
