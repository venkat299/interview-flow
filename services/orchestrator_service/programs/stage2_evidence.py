"""DSPy program for Stage-2 evidence parsing."""
from __future__ import annotations

import dspy
from pydantic import BaseModel

from gateway_service import gateway
from ..schemas import EvidenceOutput


class EvidenceInput(BaseModel):
    """User answer describing responsibilities and skills."""

    answer: str


class EvidenceProgram(dspy.Module):
    """Parse Stage-2 evidence answers into structured data."""

    system_prompt: str = (
        "From the answer, extract:"
        " skill_hooks (list of 3-5 concise items to verify later),"
        " evaluation_metrics (object of metric name to value),"
        " followup_hooks (list of technology keywords),"
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
