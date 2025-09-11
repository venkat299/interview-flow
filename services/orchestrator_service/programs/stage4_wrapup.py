"""DSPy program for Stage-4 wrap-up summarization."""
from __future__ import annotations

from typing import List

import dspy
from pydantic import BaseModel, Field

from gateway_service import gateway
from ..schemas import VerificationResult


class WrapUpInput(BaseModel):
    """Notes and verification outcomes accumulated during the interview."""

    notes: List[str] = Field(default_factory=list)
    verifications: List[VerificationResult] = Field(default_factory=list)


class WrapUpOutput(BaseModel):
    """Summary components extracted from the LLM."""

    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)


class WrapUpProgram(dspy.Module):
    """Generate final strengths, risks, and follow-up items."""

    system_prompt: str = (
        "Using the prior notes and verification results, produce a brief "
        "internal summary with keys strengths, risks, follow_ups. Respond in JSON."
    )

    async def __call__(self, inp: WrapUpInput) -> WrapUpOutput:
        notes_blob = "; ".join(inp.notes)
        verif_blob = "; ".join(f"{v.skill}:{v.result}" for v in inp.verifications)
        user_prompt = f"Notes: {notes_blob}\nVerifications: {verif_blob}"
        data = await gateway.execute_task(
            task_name="stage_4_summary",
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )
        return WrapUpOutput.model_validate(data)
