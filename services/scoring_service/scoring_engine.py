"""Scoring engine for aggregating interview signals."""
from typing import Dict, List


class ScoringEngine:
    """Combines multiple evaluation signals into final scores."""

    def aggregate(self, result: Dict, tests: List[Dict], rubric: Dict) -> Dict:
        """Fuse turn-level signals into sub-scores."""
        return {"correctness": result.get("score", 0), "reasoning": 0.0, "calibration": 0.0}
