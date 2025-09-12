"""DSPy programs for Stage-1 warm-up parsing."""
from __future__ import annotations

from typing import Dict, List, Optional

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


class WarmupConstraintsInput(BaseModel):
    """User answer listing key constraints."""

    answer: str


class WarmupConstraintsOutput(BaseModel):
    """Extracted constraint details."""

    constraints: List[str] = Field(default_factory=list)


class WarmupConstraintsProgram(dspy.Module):
    """Parse constraint list from an answer."""

    system_prompt: str = (
        "Extract the list of constraints from the answer. "
        'Respond with JSON {"constraints": [string]}.'
    )

    async def __call__(self, inp: WarmupConstraintsInput) -> WarmupConstraintsOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupConstraintsOutput.model_validate(data)


class WarmupConstraintInput(BaseModel):
    """User answer explaining scale or latency details."""

    answer: str


class WarmupConstraintOutput(BaseModel):
    """Extracted scale/latency/SLO information."""

    scale_latency_slo: Optional[str] = None


class WarmupConstraintProgram(dspy.Module):
    """Parse scale or latency constraints from an answer."""

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


class WarmupRoleInput(BaseModel):
    """User answer describing role and team size."""

    answer: str


class WarmupRoleOutput(BaseModel):
    """Extracted role and team size."""

    role: Optional[str] = None
    team_size: Optional[str] = None


class WarmupRoleProgram(dspy.Module):
    """Parse role context details."""

    system_prompt: str = (
        'Extract role and team_size. Respond with JSON {"role": string, "team_size": string}.'
    )

    async def __call__(self, inp: WarmupRoleInput) -> WarmupRoleOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupRoleOutput.model_validate(data)


class WarmupArchitectureInput(BaseModel):
    """User answer describing architecture and technologies."""

    answer: str


class WarmupArchitectureOutput(BaseModel):
    """Extracted architecture details."""

    architecture: Optional[str] = None
    key_technologies: List[str] = Field(default_factory=list)
    followup_hooks: List[str] = Field(default_factory=list)


class WarmupArchitectureProgram(dspy.Module):
    """Parse architecture information."""

    system_prompt: str = (
        'Extract architecture, key_technologies (list), and followup_hooks (list of technology keywords). '
        'Respond with JSON {"architecture": string, "key_technologies": [string], "followup_hooks": [string]}.'
    )

    async def __call__(self, inp: WarmupArchitectureInput) -> WarmupArchitectureOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupArchitectureOutput.model_validate(data)


class WarmupChallengeInput(BaseModel):
    """User answer describing the hardest challenge."""

    answer: str


class WarmupChallengeOutput(BaseModel):
    """Extracted hardest challenge."""

    hardest_challenge: Optional[str] = None


class WarmupChallengeProgram(dspy.Module):
    """Parse hardest challenge from answer."""

    system_prompt: str = (
        'Extract the hardest challenge. Respond with JSON {"hardest_challenge": string}.'
    )

    async def __call__(self, inp: WarmupChallengeInput) -> WarmupChallengeOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupChallengeOutput.model_validate(data)


class WarmupOutcomeInput(BaseModel):
    """User answer describing project outcomes."""

    answer: str


class WarmupOutcomeOutput(BaseModel):
    """Extracted project outcomes."""

    outcomes: Optional[str] = None
    evaluation_metrics: Dict[str, str] = Field(default_factory=dict)


class WarmupOutcomeProgram(dspy.Module):
    """Parse project outcomes."""

    system_prompt: str = (
        'Extract the project outcomes or metrics and any evaluation_metrics as key-value pairs. '
        'Respond with JSON {"outcomes": string, "evaluation_metrics": {string: string}}.'
    )

    async def __call__(self, inp: WarmupOutcomeInput) -> WarmupOutcomeOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupOutcomeOutput.model_validate(data)


class WarmupReflectionInput(BaseModel):
    """User answer describing lessons learned."""

    answer: str


class WarmupReflectionOutput(BaseModel):
    """Extracted lessons learned."""

    lessons: Optional[str] = None


class WarmupReflectionProgram(dspy.Module):
    """Parse lessons learned from answer."""

    system_prompt: str = (
        'Extract the lessons. Respond with JSON {"lessons": string}.'
    )

    async def __call__(self, inp: WarmupReflectionInput) -> WarmupReflectionOutput:
        data = await gateway.execute_task(
            task_name="stage_1_parse",
            system_prompt=self.system_prompt,
            user_prompt=inp.answer,
        )
        return WarmupReflectionOutput.model_validate(data)
