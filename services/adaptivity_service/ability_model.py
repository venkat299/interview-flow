"""Ability model for adaptive difficulty selection."""
from typing import Any, Dict


class AbilityModel:
    """Tracks ability estimates per skill and recommends next topics."""

    def __init__(self) -> None:
        self.abilities: Dict[str, float] = {}

    def update(self, skill: str, response: Dict[str, Any], time_taken: float) -> None:
        """Update posterior ability estimate for a skill."""
        delta = response.get("score", 0)
        self.abilities[skill] = self.abilities.get(skill, 0.0) + delta

    def recommend_next(self) -> Dict[str, Any]:
        """Recommend next skill and level based on current abilities."""
        skill = max(self.abilities, key=self.abilities.get, default="general")
        return {"skill": skill, "level": 3}
