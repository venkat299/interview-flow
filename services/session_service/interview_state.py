"""State management for stage-based interview sessions."""

from typing import List, Optional

from orchestrator_service.schemas import ContextPacket


class InterviewState:
    """Tracks the shared context packet and phase progression."""

    phases: List[str] = ["warm_up", "evidence", "theory", "wrap_up"]
    warmup_steps: List[str] = [
        "select_project",
        "role_context",
        "architecture",
        "constraints",
        "challenge",
        "outcome",
        "reflection",
    ]

    def __init__(
        self,
        packet: ContextPacket,
        session_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> None:
        self.packet = packet
        self.phase_index = 0
        # Stage-1 warm-up progresses through enumerated steps
        self.warmup_index = 0
        # Metadata for logging
        self.session_id = session_id
        self.candidate_id = candidate_id
        # Track the last question asked to pair with the next answer
        self.last_question_text: Optional[str] = None
        self.last_question_type: Optional[str] = None

    @property
    def current_phase(self) -> str:
        return self.phases[self.phase_index]

    def advance_phase(self) -> None:
        """Move to the next interview phase if available."""
        if self.phase_index < len(self.phases) - 1:
            self.phase_index += 1

    @property
    def current_warmup_step(self) -> str:
        return self.warmup_steps[self.warmup_index]

    def advance_warmup_step(self) -> None:
        if self.warmup_index < len(self.warmup_steps) - 1:
            self.warmup_index += 1
        else:
            # No more warm-up steps; advance to next phase
            self.advance_phase()

    def decrement_time(self, minutes: int) -> None:
        """Convenience helper to reduce remaining interview time."""
        remaining = self.packet.time_remaining_min or self.packet.duration_min
        self.packet.time_remaining_min = max(remaining - minutes, 0)

