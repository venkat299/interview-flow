# Application Flow

This document describes the end-to-end flow of the AI interview application, detailing how each service is initiated and interacts during a session.

## Stage Overview
- **Stage 0** – analyze the job description and resume to initialize context and timers.
- **Stage 1** – warm-up prompts gather project background and constraints.
- **Stage 2** – evidence questions collect skill hooks and confidence ratings.
- **Stage 3** – verification turns check fundamentals for each hook.
- **Stage 4** – wrap-up summarizes strengths, risks, and follow-ups.

## 1. Service Startup
1. **FastAPI application** (`services/api_service/app/main.py`)
    - Creates `FastAPI` instance; adds CORS middleware.
    - Registers REST endpoints for question generation, blueprint creation, answer evaluation, sample data, sessions, and report downloads.
    - On `startup`, seeds the sample SQLite database via `sample_data_service`.

2. **WebSocket Connection Manager** (`services/session_service/service.py`)
    - Instantiated in `main.py` as `ws_manager`.
    - Manages session state, history, runtime limits, and socket I/O.

3. **AI Gateway** (`services/gateway_service/ai_gateway.py`)
    - Initializes on import; loads YAML model routing config.
    - Exposes `gateway.execute_task` for LLM interactions used by orchestration helpers.

## 2. Session Initiation
1. **Client handshake**
    - Frontend (`test_frontend/chat.js`) opens WebSocket to `/api/v1/ws/{session_id}`.
    - On `open`, client emits `join_session` with job description, resume, and optional `time_limit` / `word_limit`.

2. **Connection Manager.connect**
    - Accepts connection, associates `session_id` with the socket.

3. **Stage‑0 Analysis**
    - `handle_message('join_session')` calls `analyze_jd_resume` (in `orchestrator_service.llm_api`).
    - Persists a session row in SQLite via `session_service.database.create_session`.
    - Emits `session_started`, current `stage`, and a compact `blueprint` payload inferred from Stage‑0.

4. **Initial Question**
    - Creates `InterviewState` and calls `Orchestrator.loop` to get the first question.
    - Persists the interviewer question and emits `new_question`.

## 3. Question–Answer Loop
1. **Candidate responds**
    - Client emits `send_answer` (or `candidate_answer`) with text.

2. **Stage flow**
    - Manager logs the answer and calls `Orchestrator.loop(state, answer)`.
    - If the stage advances, emits `stage_changed` with the new stage.
    - If another question is returned, it is persisted and emitted via `new_question`.
    - If `None` is returned, the interview has concluded (wrap‑up complete).

## 4. Termination
1. **End Interview**
    - When orchestration returns `None`, emits `interview_ended` and closes the socket.
    - `session_service.report.generate_report_pdf` is available via REST to download a PDF summary of any stored session.

## 5. Post-Interview Retrieval
1. **REST Endpoints** (`services/api_service/app/main.py`)
    - `/api/v1/sessions` lists stored sessions.
    - `/api/v1/sessions/{id}` retrieves session metadata and conversation turns.
    - `/api/v1/sessions/{id}/report` generates PDF using `session_service.report.generate_report_pdf`.

2. **Sample Data Endpoints**
    - `/job-postings`, `/job-postings/{job_id}` list and fetch seed postings.
    - `/candidate-resumes` (POST) upserts a resume; `/candidate-resumes/{candidate_id}` fetches it.
    - `/app-test/generate-candidate/{job_id}` synthesizes a profile/resume via the gateway.

---

This flow reflects the lifecycle from service startup through session management, stage‑based orchestration, and reporting.
