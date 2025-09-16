"""State management for stage-based interview sessions."""

from typing import List, Optional

from orchestrator_service.schemas import ContextPacket


class InterviewState:
    """Tracks the shared context packet and phase progression."""

    phases: List[str] = ["intro", "qa", "theory", "wrap_up"]
    theory_steps: List[str] = [
        "primary",
        "followup",
    ]
    wrapup_steps: List[str] = [
        "feedback",
    ]

    def __init__(
        self,
        packet: ContextPacket,
        session_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        job_id: Optional[str] = None,
        resume_id: Optional[str] = None,
    ) -> None:
        self.packet = packet
        self.phase_index = 0
        self.wrapup_index = 0
        self.qa_queue: List[dict] = []
        self.qa_queue_index = 0

        # Metadata for logging
        self.session_id = session_id
        self.candidate_id = candidate_id
        self.job_id = job_id
        self.resume_id = resume_id
        # Track the last question asked to pair with the next answer
        self.last_question_text: Optional[str] = None
        self.last_question_type: Optional[str] = None
        self.probed_followup_hooks: set[str] = set()
        self.last_followup_hook: Optional[str] = None
        self.last_focus_area: Optional[str] = None


    @property
    def current_phase(self) -> str:
        return self.phases[self.phase_index]

    def advance_phase(self) -> None:
        """Move to the next interview phase if available."""
        if self.phase_index < len(self.phases) - 1:
            self.phase_index += 1

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

    def ensure_qa_queue(self, focus_areas: List) -> None:
        """Populate the QA queue from the provided focus areas if empty."""

        if self.qa_queue:
            return

        self.qa_queue_index = 0
        queue: List[dict] = []
        for area in focus_areas:
            name = getattr(area, "area_name", "") or ""
            if not name:
                continue
            reasoning = list(getattr(area, "reasoning_questions", []) or [])
            conceptual = list(getattr(area, "conceptual_questions", []) or [])
            for question in reasoning[:2]:
                if question:
                    queue.append(
                        {
                            "focus_area": name,
                            "question_type": "reasoning",
                            "text": question,
                        }
                    )
            for question in conceptual[:2]:
                if question:
                    queue.append(
                        {
                            "focus_area": name,
                            "question_type": "conceptual",
                            "text": question,
                        }
                    )
        self.qa_queue = queue

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
