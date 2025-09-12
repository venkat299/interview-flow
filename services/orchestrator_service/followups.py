"""Keyword-based follow-up question templates.

Provides helper utilities to detect technology keywords in
candidate answers and to generate targeted follow-up questions.
"""
from __future__ import annotations

from typing import Dict, List

from .schemas import ContextPacket

# Mapping from lowercase keyword to question template. The template may
# reference ``{keyword}`` to inject the matched term.
FOLLOWUP_TEMPLATES: Dict[str, str] = {
    "kafka": "How did you use {keyword} in the project?",
    "kubernetes": "What challenges did you face managing deployments on {keyword}?",
}


def extract_followup_hooks(text: str) -> List[str]:
    """Return list of keywords found in ``text`` matching templates."""
    lowered = text.lower()
    return [k for k in FOLLOWUP_TEMPLATES if k in lowered]


def build_followup_question(keyword: str) -> str | None:
    """Create a follow-up question for the given keyword.

    Parameters
    ----------
    keyword: str
        The matched technology keyword.

    Returns
    -------
    str | None
        A formatted follow-up question or ``None`` if no template exists.
    """
    template = FOLLOWUP_TEMPLATES.get(keyword.lower())
    if not template:
        return None
    return (
        f"You mentioned {keyword} earlier but didn't elaborate. "
        f"{template.format(keyword=keyword)}"
    )


def _is_substantive(text: str, threshold: int = 8) -> bool:
    """Heuristic check if ``text`` seems like an explanation."""
    return len(text.split()) >= threshold


def _has_explanation(text: str, hook: str, min_follow_words: int = 3) -> bool:
    """Return True if ``text`` includes at least ``min_follow_words`` after ``hook``."""
    lowered = text.lower()
    idx = lowered.find(hook.lower())
    if idx == -1:
        return False
    after = lowered[idx + len(hook) :].split()
    return len(after) >= min_follow_words


def update_followup_hooks(
    packet: ContextPacket, answer: str, addressed_hook: str | None = None
) -> None:
    """Scan ``answer`` for keywords, update hooks, and mark resolved ones."""

    hooks_in_answer = extract_followup_hooks(answer)

    for hook in hooks_in_answer:
        if hook not in packet.followup_hooks:
            packet.followup_hooks.append(hook)
        if hook not in packet.project_context.followup_hooks:
            packet.project_context.followup_hooks.append(hook)
        if _has_explanation(answer, hook) and hook not in packet.resolved_followup_hooks:
            packet.resolved_followup_hooks.append(hook)

    if addressed_hook and addressed_hook not in packet.resolved_followup_hooks:
        if _is_substantive(answer):
            packet.resolved_followup_hooks.append(addressed_hook)
