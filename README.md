# Smart Screener AI

## 1. Project Objective

The goal of this project is to develop an AI-powered technical screening platform that automates initial interviews. The system provides a dynamic, chat-based experience for candidates, asking intelligent, context-aware follow-up questions based on the job description and the candidate's live answers. This aims to provide a deeper, more accurate signal of a candidate's abilities than traditional coding tests.

## 2. Technical Approach

The platform is built on a modern, scalable backend using a **microservices architecture**.

* **Language & Framework**: The entire backend is built with **Python** and **FastAPI**, chosen for its high performance and asynchronous capabilities.
* **Orchestrator**: A central decision layer that owns pacing, logging and agenda coverage. It pulls in helper services to pick questions, score answers and store results.
* **Helper Services**: Modular packages in `services/` provide distinct responsibilities:
  * `interviewer_service` – phrasing questions and follow-ups.
  * `monitor_service` – shadow evaluation, guardrails and timing nudges.
  * `scoring_service` – aggregates test results and rubric ratings into final scores.
  * `question_service` – seed bank management and on-the-fly generation.
  * `sandbox_service` – code and SQL execution sandboxes.
  * `verification_service` – resume-claim probing utilities.
  * `analytics_service`, `guardrails_service`, `adaptivity_service`, and `evidence_service` supply metrics, safety filters, ability models and resume parsing.
* **Real-Time Interaction**: The orchestration service exposes **WebSocket** endpoints to run live interviews and persists transcripts in SQLite via `storage_service`.
* **Development & Deployment**: All services are bundled into a single container using **Docker**. The image copies the entire repository and sets `PYTHONPATH=/code/services` so each module can be imported. Local development is driven with **Docker Compose**, ensuring a consistent and reproducible environment.

## 3. Local Development

Run the service with Docker Compose:

1. Copy the example environment file and provide your own credentials:

   ```bash
   cp services/gateway_service/.env.example services/gateway_service/.env
   ```

   Update `services/gateway_service/.env` with real values for `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `GEMINI_API_KEY`, and `LOCAL_LLM_URL`.

   When using an LLM running on your host machine (e.g., LM Studio), set
   `LLM_PROVIDER=local` and point `LOCAL_LLM_URL` to the host using
   `host.docker.internal`. For example:

   ```bash
   LOCAL_LLM_URL=http://host.docker.internal:1234/v1/chat/completions
   ```

2. Start the container:

   ```bash
   docker-compose up --build
   ```

   The compose file builds from the repository root using
   `services/api_service/Dockerfile`. The image copies the whole
   project and sets `PYTHONPATH=/code/services`, allowing the orchestrator to
   import every helper service with live reload.

### Direct service calls

The WebSocket session management is now embedded in the orchestration service
and calls orchestration functions in‑process for lower latency.


## 4. Test Frontend & End-to-End Testing

Once the backend service is running, you can drive a sample interview using the lightweight test frontend located in `test_frontend/`.

1. Start the services if they are not already running:

   ```bash
   docker-compose up --build
   ```

2. In a new terminal, serve the static files:

   ```bash
   python -m http.server --directory test_frontend 3000
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser. The page connects to the service and lets you exchange messages with the AI interviewer.


## 5. WebSocket & Session Retrieval

The API service exposes WebSocket and read endpoints:

- WebSocket: `ws://localhost:8003/api/v1/ws/{session_id}`
- `GET http://localhost:8003/api/v1/sessions` — list sessions with start/end times.
- `GET http://localhost:8003/api/v1/sessions/{session_id}` — fetch a session with parsed `blueprint`, `rubric`, `transcript`, and the per-turn `turns` log.

Adjust the base URL/port to match your deployment.

## 6. Logging & Tracing

Configure verbosity via environment variables (consumed by `gateway_service.config.Settings`):

- `LOG_LEVEL`: One of `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Use `TRACE` for the most granular output.
- `TRACE_CALLS`: Set to `true`/`1` to log function CALL/RETURN events across service modules.
- `TRACE_MODULE_PREFIXES`: Comma-separated module prefixes to trace (e.g., `api_service,orchestrator_service`). If empty, path-based filter applies.
- `TRACE_FILE_PATH_CONTAINS`: Comma-separated path substrings; any file path containing one is traced. Default: `services/` (traces all repo-owned code).
- `TRACE_CONCISE`: If `true`, prints concise trace lines without timestamp/level, e.g., `CALL module.func` and `RET module.func`.

Example `.env` snippet to enable deep tracing:

```
LOG_LEVEL=TRACE
TRACE_CALLS=true
# You can leave module prefixes empty and rely on path filter
TRACE_MODULE_PREFIXES=
TRACE_FILE_PATH_CONTAINS=services/
TRACE_CONCISE=true
```

With tracing enabled, the app logs every function call/return for modules matching the prefixes, e.g.:

```
2025-01-01 12:00:00 TRACE trace.calls CALL services.session_service.service.handle_message (/code/services/session_service/service.py:69)
2025-01-01 12:00:00 TRACE trace.calls RET  services.session_service.service.handle_message
```
