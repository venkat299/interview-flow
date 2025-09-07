"""WebSocket session manager wired to AI orchestration functions."""
import random
import time
from typing import Dict, List, Optional

from fastapi import WebSocket

from orchestrator_service import Orchestrator

from orchestrator_service.schemas import (
    InterviewContext,
    EvaluationRequest,
    TopicBlueprint,
)
from orchestrator_service.llm_api import (
    create_interview_blueprint,
    evaluate_candidate_answer,
    generate_final_summary,
    generate_next_question,
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
        self.orchestrator = Orchestrator()

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
            end_session(session_id, rubric, transcript, duration, words, ended_by="system")
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
            await self.orchestrator.record_turn({"role": "interviewer", "message": question})
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
            await self.orchestrator.record_turn({"role": "candidate", "message": answer})
            await websocket.send_json({"event": "interviewer_typing"})
            state = self.states.get(websocket)
            if state and state.current_phase == "technical":
                evaluation_result = await self._evaluate_answer(state, conversation, websocket, answer)
                state.update_state_after_answer(evaluation_result)
                if state.should_switch_topic():
                    state.get_next_topic()
            else:
                evaluation_result = {}
            if session_id:
                log_turn(session_id, "candidate", answer, evaluation_result or None)
            await websocket.send_json({"event": "evaluation", "payload": evaluation_result})
            await self.on_turn_complete(evaluation_result)
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
            await self.orchestrator.record_turn({"role": "interviewer", "message": question})
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

        elif event == "skip_question":
            conversation.append({"role": "candidate", "message": "[skipped]"})
            await self.orchestrator.record_turn({"role": "candidate", "message": "[skipped]"})
            if session_id:
                log_turn(session_id, "candidate", "[skipped]", {"skipped": True})
            state = self.states.get(websocket)
            if state:
                state.advance_phase()
            question = await self._next_question(websocket, conversation)
            conversation.append({"role": "interviewer", "message": question})
            self.last_question[websocket] = question
            if session_id:
                log_turn(session_id, "interviewer", question)
            await self.orchestrator.record_turn({"role": "interviewer", "message": question})
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
            final_score = None
            summary = None
            if state:
                result = await generate_final_summary(state.performance_log)
                final_score = result.get("final_score") if isinstance(result, dict) else None
                summary = result.get("summary") if isinstance(result, dict) else None
            if session_id:
                transcript = list(self.history.get(websocket) or [])
                duration = int(time.time() - self.start_time.get(websocket, time.time()))
                words = self.word_count.get(websocket, 0)
                end_session(session_id, rubric, transcript, duration, words, final_score, summary, ended_by="user")
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
            end_session(session_id, rubric, transcript, duration, words, ended_by="system")
        self.ended[websocket] = True
        await websocket.send_json({"event": "interview_ended"})
        await websocket.close()

    async def _next_question(self, websocket: WebSocket, history: List[dict]) -> str:
        context_dict = self.contexts.get(websocket, {"job_description": ""})
        state = self.states.get(websocket)
        persona = self.persona.get(websocket) or "friendly_mentor"
        return await self.orchestrator.loop(
            state,
            context_dict,
            history,
            persona,
            generate_next_question,
        )


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
        data = result.model_dump()
        data["topic"] = topic_dict.get("name") if isinstance(topic_dict, dict) else None
        data["difficulty"] = self._depth_to_difficulty(state.difficulty)
        return data

    async def on_turn_complete(self, result: dict) -> None:
        """Hook for monitor and scoring modules to observe turn results."""
        _ = result  # placeholder to satisfy type checkers
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
