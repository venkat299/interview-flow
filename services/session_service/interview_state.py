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
    evidence_steps: List[str] = [
        "components",
        "choice_space",
        "decision_rationale",
        "outcome_validation",
        "tradeoff_reflection",
    ]
    theory_steps: List[str] = [
        "primary",
        "followup",
    ]
    wrapup_steps: List[str] = [
        "candidate_questions",
        "feedback",
    ]

    def __init__(
        self,
        packet: ContextPacket,
        session_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> None:
        self.packet = packet
        self.phase_index = 0
        # Stage-based step indexes
        self.warmup_index = 0
        self.evidence_index = 0
        self.theory_index = 0
        self.theory_skill_index = 0
        self.wrapup_index = 0

        # Metadata for logging
        self.session_id = session_id
        self.candidate_id = candidate_id
        # Track the last question asked to pair with the next answer
        self.last_question_text: Optional[str] = None
        self.last_question_type: Optional[str] = None
        self.probed_followup_hooks: set[str] = set()


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

    @property
    def current_evidence_step(self) -> str:
        return self.evidence_steps[self.evidence_index]

    def advance_evidence_step(self) -> None:
        if self.evidence_index < len(self.evidence_steps) - 1:
            self.evidence_index += 1
        else:
            self.advance_phase()

    @property
    def current_theory_step(self) -> str:
        return self.theory_steps[self.theory_index]

    def advance_theory_step(self) -> None:
        if self.theory_index < len(self.theory_steps) - 1:
            self.theory_index += 1
        else:
            self.theory_index = 0
            self.theory_skill_index += 1
            skills = (
                self.packet.followup_hooks
                or self.packet.skill_hooks
                or self.packet.jd_core_skills
            )
            if self.theory_skill_index >= len(skills):
                self.advance_phase()

    @property
    def current_wrapup_step(self) -> str:
        return self.wrapup_steps[self.wrapup_index]

    def advance_wrapup_step(self) -> None:
        if self.wrapup_index < len(self.wrapup_steps) - 1:
            self.wrapup_index += 1
        else:
            self.wrapup_index += 1
            self.advance_phase()

    def decrement_time(self, minutes: int) -> None:
        """Convenience helper to reduce remaining interview time."""
        remaining = self.packet.time_remaining_min or self.packet.duration_min
        self.packet.time_remaining_min = max(remaining - minutes, 0)

