"""State management for stage-based interview sessions."""

from typing import List, Optional

from orchestrator_service.schemas import ContextPacket


class InterviewState:
    """Tracks the shared context packet and phase progression."""

    phases: List[str] = ["experience", "theory", "wrap_up"]
    default_experience_steps: List[str] = [
        "select_project",
        "project_overview",
        "role",
        "team_size",
        "architecture",
        "tech_stack",
        "constraints",
        "challenge",
        "resolution",
        "outcome",
        "reflection",
        "components_list",
        "component_details",
        "choice_space",
        "decision_rationale",
        "outcome_validation",
        "tradeoff_exploration",
        "tradeoff_reasoning",
    ]
    theory_steps: List[str] = [
        "primary",
        "followup",
    ]
    wrapup_steps: List[str] = [
        "feedback",
        "closing",
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
        plan = list(packet.experience_plan or [])
        if not plan:
            plan = list(self.default_experience_steps)
        self.experience_plan: List[str] = plan
        self.experience_index = 0
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
        self.last_followup_hook: Optional[str] = None


    @property
    def current_phase(self) -> str:
        return self.phases[self.phase_index]

    def advance_phase(self) -> None:
        """Move to the next interview phase if available."""
        if self.phase_index < len(self.phases) - 1:
            self.phase_index += 1

    @property
    def current_experience_step(self) -> Optional[str]:
        if self.experience_index >= len(self.experience_plan):
            return None
        return self.experience_plan[self.experience_index]

    def advance_experience_step(self) -> None:
        if self.experience_index < len(self.experience_plan) - 1:
            self.experience_index += 1
        else:
            self.experience_index += 1
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
