"""State management for stage-based interview sessions."""

from typing import List

from orchestrator_service.schemas import ContextPacket


class InterviewState:
    """Tracks the shared context packet and phase progression."""

    phases: List[str] = ["warm_up", "evidence", "theory", "wrap_up"]

    def __init__(self, packet: ContextPacket) -> None:
        self.packet = packet
        self.phase_index = 0
        # Stage-1 warm-up consists of two questions; track progress
        self.warmup_step = 0

    @property
    def current_phase(self) -> str:
        return self.phases[self.phase_index]

    def advance_phase(self) -> None:
        """Move to the next interview phase if available."""
        if self.phase_index < len(self.phases) - 1:
            self.phase_index += 1

    def decrement_time(self, minutes: int) -> None:
        """Convenience helper to reduce remaining interview time."""
        remaining = self.packet.time_remaining_min or self.packet.duration_min
        self.packet.time_remaining_min = max(remaining - minutes, 0)

