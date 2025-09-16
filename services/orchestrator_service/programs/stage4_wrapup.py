"""DSPy program for Stage-4 wrap-up summarization."""
from __future__ import annotations

from typing import Any, List

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

    @staticmethod
    def _followup_to_text(item: Any) -> str:
        """Coerce mixed follow-up payloads into displayable strings."""

        if isinstance(item, str):
            return item.strip()

        if isinstance(item, dict):
            primary = None
            for key in ("question", "action", "task", "item", "text", "follow_up"):
                if item.get(key):
                    primary = str(item[key]).strip()
                    break

            reason = None
            for key in ("why", "rationale", "reason", "notes", "context"):
                if item.get(key):
                    reason = str(item[key]).strip()
                    break

            if primary and reason:
                return f"{primary} — Reason: {reason}"
            if primary:
                return primary
            if reason:
                return reason

        # Fallback to generic string conversion
        return str(item).strip()

    @classmethod
    def _normalize_followups(cls, raw: Any) -> List[str]:
        if not isinstance(raw, list):
            if raw is None:
                return []
            text = str(raw).strip()
            return [text] if text else []

        normalized: List[str] = []
        for item in raw:
            text = cls._followup_to_text(item)
            if text:
                normalized.append(text)
        return normalized

    async def __call__(self, inp: WrapUpInput) -> WrapUpOutput:
        notes_blob = "; ".join(inp.notes)
        verif_blob = "; ".join(f"{v.skill}:{v.result}" for v in inp.verifications)
        user_prompt = f"Notes: {notes_blob}\nVerifications: {verif_blob}"
        data = await gateway.execute_task(
            task_name="stage_4_summary",
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )
        if isinstance(data, dict) and "follow_ups" in data:
            data = {**data, "follow_ups": self._normalize_followups(data.get("follow_ups"))}
        return WrapUpOutput.model_validate(data)
