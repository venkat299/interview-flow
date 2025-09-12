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
    "kafka": "You mentioned Kafka earlier. How did you use Kafka in the project?",
    "kubernetes": "You mentioned Kubernetes. What challenges did you face managing deployments on Kubernetes?",
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
    return template.format(keyword=keyword)


def update_followup_hooks(packet: ContextPacket, answer: str) -> None:
    """Scan ``answer`` for keywords and append to packet hooks."""
    for hook in extract_followup_hooks(answer):
        if hook not in packet.followup_hooks:
            packet.followup_hooks.append(hook)
        if hook not in packet.project_context.followup_hooks:
            packet.project_context.followup_hooks.append(hook)
