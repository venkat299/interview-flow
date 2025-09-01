"""State management for an active interview session (embedded)."""
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
        self.topic_queue: Deque[Dict] = deque(topics_sorted)
        # Track difficulty level per topic (1=Fundamental, ...)
        self.topic_progress: Dict[str, int] = {
            t.get("name", f"topic_{i}"): 1 for i, t in enumerate(topics_sorted)
        }
        self.current_topic: Optional[Dict] = None
        self.difficulty_levels = {
            1: "Fundamental",
            2: "Intermediate",
            3: "Advanced",
            4: "Expert",
            5: "Expert",
        }
        self.difficulty: str = self.difficulty_levels[1]
        self.performance_log: List[Dict] = []
        self.current_phase: str = "introduction"
        self.needs_hint: bool = False

    def get_next_topic(self) -> Optional[Dict]:
        """Select the next topic ensuring lower difficulties are covered first."""
        if not self.topic_queue:
            self.current_topic = None
            return None

        # Determine the lowest difficulty level across topics
        min_level = min(self.topic_progress.values()) if self.topic_progress else 1

        for _ in range(len(self.topic_queue)):
            topic = self.topic_queue.popleft()
            self.topic_queue.append(topic)
            name = topic.get("name")
            if self.topic_progress.get(name, 1) == min_level:
                self.current_topic = topic
                self.difficulty = self.difficulty_levels[self.topic_progress[name]]
                self.needs_hint = False
                return topic

        self.current_topic = None
        return None

    def update_state_after_answer(self, evaluation_result: Dict) -> None:
        """Update internal state based on evaluation results."""
        self.performance_log.append(evaluation_result)
        score = evaluation_result.get("score", 0)
        topic_name = (self.current_topic or {}).get("name")
        if not topic_name:
            return

        level = self.topic_progress.get(topic_name, 1)
        if score >= 7 and level < 5:
            level += 1
            self.topic_progress[topic_name] = level

        # Determine if a hint should be provided on the next question
        self.needs_hint = score < 6 and level >= 4

        self.difficulty = self.difficulty_levels[level]

    def advance_phase(self) -> None:
        """Move to the next phase in the interview flow."""
        if self.current_phase == "introduction":
            self.current_phase = "soft_skills"
        elif self.current_phase == "soft_skills":
            self.current_phase = "technical"

    def should_switch_topic(self) -> bool:
        """Decide whether to switch to the next topic."""
        # Placeholder logic: never switch automatically
        return False

