"""DSPy program for Stage-2 evidence parsing."""
from __future__ import annotations

from typing import Dict, List

import dspy
from pydantic import BaseModel, Field

from gateway_service import gateway


class EvidenceInput(BaseModel):
    """User answer describing responsibilities and skill confidence."""

    answer: str


class EvidenceOutput(BaseModel):
    """Parsed skill hooks, confidence ratings, and notes."""

    skill_hooks: List[str] = Field(default_factory=list)
    confidence_ratings: Dict[str, int] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class EvidenceProgram(dspy.Module):
    """Parse Stage-2 evidence answers into structured data."""

    system_prompt: str = (
        "From the answer, extract:"
        " skill_hooks (list of 3-5 concise items to verify later),"
        " confidence_ratings (mapping skill->1-5),"
        " and notes (brief bullets)."
        " Respond with JSON containing these keys."
    )

    async def __call__(self, inp: EvidenceInput) -> EvidenceOutput:
        data = await gateway.execute_task(
            task_name="stage_2_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return EvidenceOutput.model_validate(data)
