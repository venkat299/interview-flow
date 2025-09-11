"""DSPy programs for Stage-1 warm-up parsing."""
from __future__ import annotations

from typing import List, Optional

import dspy
from pydantic import BaseModel, Field

from gateway_service import gateway


class WarmupOverviewInput(BaseModel):
    """User answer describing a project overview."""

    answer: str


class WarmupOverviewOutput(BaseModel):
    """Extracted goal and constraints from the overview."""

    goal: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)


class WarmupOverviewProgram(dspy.Module):
    """Parse project overview into structured fields."""

    system_prompt: str = (
        "Extract the project goal and list of key constraints from the answer. "
        "Respond with JSON having 'goal' and 'constraints' (list)."
    )

    async def __call__(self, inp: WarmupOverviewInput) -> WarmupOverviewOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupOverviewOutput.model_validate(data)


class WarmupConstraintInput(BaseModel):
    """User answer explaining hardest constraint."""

    answer: str


class WarmupConstraintOutput(BaseModel):
    """Extracted scale/latency/SLO details."""

    scale_latency_slo: Optional[str] = None


class WarmupConstraintProgram(dspy.Module):
    """Parse constraint details from an answer."""

    system_prompt: str = (
        "Extract any scale, latency, or SLO details from the answer. "
        'Respond with JSON {"scale_latency_slo": string}.'
    )

    async def __call__(self, inp: WarmupConstraintInput) -> WarmupConstraintOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupConstraintOutput.model_validate(data)
