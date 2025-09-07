# Application Flow

This document describes the end-to-end flow of the AI interview application, detailing how each service is initiated and interacts during a session.

## 1. Service Startup
1. **FastAPI application** (`services/api_service/app/main.py`)
    - Creates `FastAPI` instance.
    - Adds CORS middleware.
    - Registers REST endpoints for question generation, blueprint creation, answer evaluation, sample data, sessions, and report downloads.
    - On `startup`, seeds the sample SQLite database.

2. **WebSocket Connection Manager** (`services/session_service/service.py`)
    - Instantiated in `main.py` as `ws_manager`.
    - Manages session state, history, timers, and communication over WebSocket.

3. **AI Gateway** (`services/gateway_service/ai_gateway.py`)
    - Initializes on import; loads model routing config.
    - Exposes `gateway.execute_task` for LLM interactions used by orchestration functions.

## 2. Session Initiation
1. **Client handshake**
    - Frontend (`test_frontend/chat.js`) opens WebSocket to `/api/v1/ws/{session_id}`.
    - On `open`, client emits `join_session` with job description, resume, persona, and optional limits.

2. **Connection Manager.connect**
    - Accepts connection, initializes session dictionaries, associates session ID.

3. **Blueprint Generation**
    - `handle_message` receives `join_session`.
    - Calls `create_interview_blueprint` → `llm_api.create_interview_blueprint` → `gateway.execute_task` to obtain structured topics.
    - Session record created in SQLite via `create_session`.

4. **Initial Question**
    - State engine (`InterviewState`) selects first topic.
    - `_next_question` generates introductory question or soft skill question using `generate_introductory_question` / `generate_soft_skill_question`.
    - Sends `session_started`, `blueprint`, and `new_question` events to client.

## 3. Question–Answer Loop
1. **Candidate responds**
    - Client emits `send_answer` with text.

2. **Evaluation**
    - `_evaluate_answer` builds `EvaluationRequest` with last question and topic blueprint.
    - `llm_api.evaluate_candidate_answer` invokes `gateway.execute_task` to produce score, depth, confidence, truthfulness.
    - Results logged to session DB via `log_turn`; `evaluation` event sent back.

3. **State Update**
    - `InterviewState.update_state_after_answer` adjusts difficulty and topic mastery.
    - If topic complete, `get_next_topic` selects next one.
    - Phase advances (`introduction` → `soft_skills` → `technical`) as required.

4. **Next Question**
    - `_next_question` composes follow-up:
        - Builds `InterviewRequest` with context, conversation history, topic, difficulty.
        - `llm_api.generate_next_question` calls `gateway.execute_task`.
        - Prefaces question with randomized feedback string.
    - `new_question` event sent to client.

5. **Skip Question**
    - Client may send `skip_question`.
    - Manager logs skipped turn, advances phase/topic, calls `_next_question` to deliver another `new_question`.

## 4. Limits and Termination
1. **Limit Enforcement**
    - `_limits_exceeded` checks elapsed time and word count before/after each answer.
    - If exceeded, `_force_end` records session and closes socket.

2. **End Interview**
    - Client sends `end_interview` or limits trigger forced end.
    - `generate_final_summary` aggregates `performance_log` for final score and summary via LLM.
    - `end_session` persists final rubric, transcript, duration, word count, summary.
    - Sends `interview_ended` event and closes connection.

## 5. Post-Interview Retrieval
1. **REST Endpoints** (`main.py`)
    - `/api/v1/sessions` lists stored sessions.
    - `/api/v1/sessions/{id}` retrieves session metadata and conversation turns.
    - `/api/v1/sessions/{id}/report` generates PDF using `report.generate_report_pdf`.

2. **Sample Data Endpoints**
    - `/samples` and `/samples/{key}` expose seeded example prompts for testing.

---

This flow reflects the full lifecycle from service startup through session management, LLM-powered question/evaluation, and reporting.
