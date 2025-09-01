"""WebSocket session manager wired to AI orchestration functions."""
from typing import Dict, List, Optional

import random
import time

from fastapi import WebSocket

from ai_orchestration_service.schemas import (
    InterviewContext,
    ConversationTurn,
    InterviewRequest,
    EvaluationRequest,
    TopicBlueprint,
)
from ai_orchestration_service.ai_orchestration import (
    generate_next_question,
    create_interview_blueprint,
    evaluate_candidate_answer,
    generate_introductory_question,
    generate_soft_skill_question,
)
from .interview_state import InterviewState
from .database import create_session, log_turn, end_session


class ConnectionManager:
    """Connection manager for interview sessions using in-process orchestration."""

    def __init__(self) -> None:
        self.history: Dict[WebSocket, List[dict]] = {}
        self.contexts: Dict[WebSocket, dict] = {}
        self.states: Dict[WebSocket, InterviewState] = {}
        self.session_ids: Dict[WebSocket, str] = {}
        self.ended: Dict[WebSocket, bool] = {}
        self.persona: Dict[WebSocket, str] = {}
        self.last_question: Dict[WebSocket, str] = {}
        self.start_time: Dict[WebSocket, float] = {}
        self.time_limit: Dict[WebSocket, Optional[int]] = {}
        self.word_limit: Dict[WebSocket, Optional[int]] = {}
        self.word_count: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.history[websocket] = []
        self.session_ids[websocket] = session_id
        self.ended[websocket] = False

    def disconnect(self, websocket: WebSocket) -> None:
        session_id = self.session_ids.get(websocket)
        state = self.states.get(websocket)
        if session_id and not self.ended.get(websocket):
            rubric = {"performance_log": state.performance_log} if state else None
            transcript = self.history.get(websocket) or []
            duration = int(time.time() - self.start_time.get(websocket, time.time()))
            words = self.word_count.get(websocket, 0)
            end_session(session_id, rubric, transcript, duration, words)
        self.history.pop(websocket, None)
        self.contexts.pop(websocket, None)
        self.states.pop(websocket, None)
        self.session_ids.pop(websocket, None)
        self.ended.pop(websocket, None)
        self.persona.pop(websocket, None)
        self.last_question.pop(websocket, None)
        self.start_time.pop(websocket, None)
        self.time_limit.pop(websocket, None)
        self.word_limit.pop(websocket, None)
        self.word_count.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        conversation = self.history.setdefault(websocket, [])
        event = data.get("event")
        session_id = self.session_ids.get(websocket)

        if event != "join_session" and self._limits_exceeded(websocket):
            await self._force_end(websocket)
            return

        if event == "join_session":
            payload = data.get("payload", {})
            context = {
                "job_description": payload.get("job_description", ""),
                "candidate_resume": payload.get("candidate_resume", ""),
            }
            persona = payload.get("persona") or "friendly_mentor"
            self.contexts[websocket] = context
            self.persona[websocket] = persona
            tl = payload.get("time_limit")
            wl = payload.get("word_limit")
            self.time_limit[websocket] = int(tl) if tl is not None else None
            self.word_limit[websocket] = int(wl) if wl is not None else None
            self.start_time[websocket] = time.time()
            self.word_count[websocket] = 0

            # Create blueprint via orchestration
            blueprint_model = await create_interview_blueprint(InterviewContext(**context))
            blueprint = blueprint_model.model_dump()
            self.states[websocket] = InterviewState(blueprint)
            if session_id:
                create_session(session_id, blueprint, self.time_limit.get(websocket), self.word_limit.get(websocket))
            await websocket.send_json({"event": "session_started"})
            await websocket.send_json({"event": "blueprint", "payload": blueprint})

            # Prime topic and ask first question
            state = self.states.get(websocket)
            if state and state.get_next_topic():
                pass  # current_topic set
            question = await self._next_question(websocket, conversation)
            conversation.append({"role": "interviewer", "message": question})
            self.last_question[websocket] = question
            if session_id:
                log_turn(session_id, "interviewer", question)
            # Include topic and difficulty metadata for clients
            topic_name = (self.states.get(websocket).current_topic or {}).get("name") if self.states.get(websocket) else None
            diff_num = self._depth_to_difficulty(self.states.get(websocket).difficulty) if self.states.get(websocket) else 3
            await websocket.send_json(
                {
                    "event": "new_question",
                    "payload": {
                        "question_text": question,
                        "topic": topic_name,
                        "difficulty": diff_num,
                    },
                }
            )

        elif event == "send_answer":
            answer = data.get("payload", {}).get("answer_text", "")
            conversation.append({"role": "candidate", "message": answer})
            self.word_count[websocket] = self.word_count.get(websocket, 0) + len(answer.split())
            await websocket.send_json({"event": "interviewer_typing"})
            state = self.states.get(websocket)
            if state and state.current_phase == "technical":
                evaluation_result = await self._evaluate_answer(state, conversation, websocket, answer)
                state.update_state_after_answer(evaluation_result)
            else:
                evaluation_result = {}
            if session_id:
                log_turn(session_id, "candidate", answer, evaluation_result or None)
            await websocket.send_json({"event": "evaluation", "payload": evaluation_result})
            if self._limits_exceeded(websocket):
                await self._force_end(websocket)
                return
            if state:
                state.advance_phase()
            question = await self._next_question(websocket, conversation)
            conversation.append({"role": "interviewer", "message": question})
            self.last_question[websocket] = question
            if session_id:
                log_turn(session_id, "interviewer", question)
            topic_name = (self.states.get(websocket).current_topic or {}).get("name") if self.states.get(websocket) else None
            diff_num = self._depth_to_difficulty(self.states.get(websocket).difficulty) if self.states.get(websocket) else 3
            await websocket.send_json(
                {
                    "event": "new_question",
                    "payload": {
                        "question_text": question,
                        "topic": topic_name,
                        "difficulty": diff_num,
                    },
                }
            )

        elif event == "end_interview":
            state = self.states.get(websocket)
            rubric = {"performance_log": state.performance_log} if state else None
            if session_id:
                transcript = list(self.history.get(websocket) or [])
                duration = int(time.time() - self.start_time.get(websocket, time.time()))
                words = self.word_count.get(websocket, 0)
                end_session(session_id, rubric, transcript, duration, words)
            self.ended[websocket] = True
            await websocket.send_json({"event": "interview_ended"})
            await websocket.close()

    def _limits_exceeded(self, websocket: WebSocket) -> bool:
        tl = self.time_limit.get(websocket)
        start = self.start_time.get(websocket)
        if tl and start and (time.time() - start) >= tl:
            return True
        wl = self.word_limit.get(websocket)
        if wl and self.word_count.get(websocket, 0) >= wl:
            return True
        return False

    async def _force_end(self, websocket: WebSocket) -> None:
        session_id = self.session_ids.get(websocket)
        state = self.states.get(websocket)
        rubric = {"performance_log": state.performance_log} if state else None
        if session_id:
            transcript = list(self.history.get(websocket) or [])
            duration = int(time.time() - self.start_time.get(websocket, time.time()))
            words = self.word_count.get(websocket, 0)
            end_session(session_id, rubric, transcript, duration, words)
        self.ended[websocket] = True
        await websocket.send_json({"event": "interview_ended"})
        await websocket.close()

    async def _next_question(self, websocket: WebSocket, history: List[dict]) -> str:
        context_dict = self.contexts.get(websocket, {"job_description": ""})
        state = self.states.get(websocket)
        if state and state.current_phase == "introduction":
            return await generate_introductory_question()
        if state and state.current_phase == "soft_skills":
            resume = context_dict.get("candidate_resume", "")
            return await generate_soft_skill_question(resume)
        topic_name = (state.current_topic or {}).get("name") if state else None
        difficulty_num = self._depth_to_difficulty(state.difficulty) if state else 3
        req = InterviewRequest(
            context=InterviewContext(**context_dict),
            history=[ConversationTurn(**t) for t in history],
            current_topic=topic_name or "General",
            current_difficulty=difficulty_num,
            persona=self.persona.get(websocket) or "friendly_mentor",
            needs_hint=getattr(state, "needs_hint", False),
        )
        feedback_options = [
            "Great, let's move on.",
            "Thanks for sharing. Now, let's consider this...",
            "Good insight. Here's another one:",
        ]
        feedback = random.choice(feedback_options)
        question = await generate_next_question(req)
        return f"{feedback} {question}"

    async def _evaluate_answer(
        self,
        state: InterviewState,
        history: List[dict],
        websocket: WebSocket,
        answer: str,
    ) -> dict:
        last_q = self.last_question.get(websocket) or ""
        topic_dict = state.current_topic if state else None
        if not topic_dict:
            return {"score": 0, "assessed_depth": "Intermediate", "llm_confidence": "Low", "justification": "No topic selected.", "is_truthful": True}
        eval_req = EvaluationRequest(
            question=last_q,
            answer=answer,
            topic_blueprint=TopicBlueprint(**topic_dict),
        )
        result = await evaluate_candidate_answer(eval_req)
        return result.model_dump()

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
