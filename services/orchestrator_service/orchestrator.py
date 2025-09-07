"""Lightweight orchestrator coordinating interview flow."""
from typing import List, Dict, Optional, Callable

from .schemas import (
    InterviewContext,
    ConversationTurn,
    InterviewRequest,
)
from .llm_api import (
    generate_introductory_question,
    generate_soft_skill_question,
)


class Orchestrator:
    """Owns agenda decisions and turn logging for sessions."""

    async def run_session(self, session_ctx: Dict) -> None:
        """Drive session-level pacing and dispatch.

        Parameters
        ----------
        session_ctx: Dict
            Contextual information about the interview session.
        """
        # Placeholder for future loop/timer management
        return None

    async def decide_next_action(
        self,
        state,
        context: Dict,
        history: List[Dict],
        persona: Optional[str] = None,
        question_func=None,
        random_choice: Optional[Callable[[List[str]], str]] = None,
    ) -> str:
        """Choose the next question based on state and history."""
        if state and state.current_phase == "introduction":
            return await generate_introductory_question()
        if state and state.current_phase == "soft_skills":
            resume = context.get("candidate_resume", "")
            return await generate_soft_skill_question(resume)
        topic_name = (state.current_topic or {}).get("name") if state else None
        difficulty_num = self._depth_to_difficulty(state.difficulty) if state else 3
        req = InterviewRequest(
            context=InterviewContext(**context),
            history=[ConversationTurn(**t) for t in history],
            current_topic=topic_name or "General",
            current_difficulty=difficulty_num,
            persona=persona or "friendly_mentor",
            needs_hint=getattr(state, "needs_hint", False),
        )
        quality = getattr(state, "last_answer_quality", "neutral") if state else "neutral"
        if quality == "correct":
            options = [
                "Great job!", "Nice work. Let's keep going.", "Excellent answer. Here's the next one:",
            ]
        elif quality == "incorrect":
            options = [
                "Thanks for trying. Let's take a step back.",
                "No worries, we can look at an easier one.",
                "Good effort. Let's tackle this from another angle:",
            ]
        else:
            options = [
                "Thanks for sharing. Now, let's consider this...",
                "Good insight. Here's another one:",
                "Alright, let's move on.",
            ]
        if random_choice is None:
            import random
            random_choice = random.choice

        feedback = random_choice(options)
        if question_func is None:
            raise ValueError("question_func must be provided")
        question = await question_func(req)
        return f"{feedback} {question}"

    async def loop(
        self,
        state,
        context: Dict,
        history: List[Dict],
        persona: Optional[str],
        question_func,
    ) -> str:
        """Orchestrate monitor → bank → interviewer → tools → scoring.

        This minimal implementation delegates to ``decide_next_action`` and
        returns the next question string."""
        return await self.decide_next_action(state, context, history, persona, question_func)


    async def record_turn(self, turn: Dict) -> None:
        """Persist transcript turn and metadata."""
        # Placeholder for storage layer integration
        return None

    @staticmethod
    def _depth_to_difficulty(depth: str) -> int:
        s = str(depth or "").lower()
        if s in ("fundamental", "beginner", "basic"):
            return 1
        if s == "intermediate":
            return 3
        if s == "advanced":
            return 4
        if s == "expert":
            return 5
        return 3
