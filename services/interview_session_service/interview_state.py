"""State management for an active interview session."""
from collections import deque
from typing import Deque, Dict, List, Optional


class InterviewState:
    """Holds state for a single interview session."""

    def __init__(self, blueprint: Dict) -> None:
        self.blueprint = blueprint
        topics = blueprint.get("topics", [])
        topics_sorted = sorted(
            topics, key=lambda t: t.get("relevance_to_role", 0), reverse=True
        )
        self._topics: Deque[Dict] = deque(topics_sorted)
        self.current_topic: Optional[Dict] = None
        self.difficulty: str = "Fundamental"
        self.performance_log: List[Dict] = []

    def get_next_topic(self) -> Optional[Dict]:
        """Pop the next topic from the queue and reset difficulty."""
        if self._topics:
            self.current_topic = self._topics.popleft()
            self.difficulty = "Fundamental"
        else:
            self.current_topic = None
        return self.current_topic

    def update_state_after_answer(self, evaluation_result: Dict) -> None:
        """Update internal state based on evaluation results."""
        self.performance_log.append(evaluation_result)
        score = evaluation_result.get("score", 0)
        if score > 7:
            self.difficulty = "Advanced"
        elif score > 4:
            self.difficulty = "Intermediate"
        else:
            self.difficulty = "Fundamental"

    def should_switch_topic(self) -> bool:
        """Decide whether to switch to the next topic."""
        # Placeholder logic: never switch automatically
        return False

