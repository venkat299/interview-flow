# Application Flow

This document outlines the lifecycle of an interview from startup through reporting.

## 1. Startup

- `services/api_service/app/main.py` creates the FastAPI app, adds CORS, registers REST routes and seeds the sample database.
- `services/session_service/service.py` instantiates `ConnectionManager` to manage sockets, state, and persistence.
- `services/gateway_service/ai_gateway.py` loads `llm_router_config.yml` and exposes `gateway.execute_task` for LLM calls.

## 2. Session Start

1. The client opens `ws://.../api/v1/ws/{session_id}` and sends `join_session` with a job description and resume.
2. `ConnectionManager.connect` registers the socket.
3. `llm_api.analyze_jd_resume` builds the initial context packet, stores a session row, and emits `session_started` with the interview blueprint.
4. The orchestrator emits the first `new_question`.

## 3. Question Loop

1. Each answer from the client is persisted and passed to `Orchestrator.loop`.
2. The orchestrator advances stages (warm‑up, evidence, theory, wrap‑up) and may emit `stage_changed`.
3. A subsequent question is returned via `new_question` until the orchestrator returns `None`.

## 4. Termination

- When no further questions remain, the server emits `interview_ended` and closes the socket.
- A PDF summary can be requested with `GET /api/v1/sessions/{id}/report`.

## 5. Retrieval

- `GET /api/v1/sessions` lists stored sessions.
- `GET /api/v1/sessions/{id}` returns metadata, blueprint, and transcript.
