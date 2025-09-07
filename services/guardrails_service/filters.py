"""Guardrail utilities for safety and privacy."""
from typing import Dict

BLOCKED_TERMS = {"race", "religion", "gender"}


async def check_question(text: str) -> bool:
    """Return False if question violates safety policies."""
    lowered = text.lower()
    return not any(term in lowered for term in BLOCKED_TERMS)


async def anonymize_logs(turn: Dict) -> Dict:
    """Scrub personally identifiable information from a turn."""
    # Placeholder: simply return the turn unchanged
    return dict(turn)
