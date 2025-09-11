# Interview Flow

Interview Flow is an AI‑powered technical screening platform built from small Python services.
It conducts staged interviews over WebSocket, routes LLM calls through a gateway, and persists transcripts for later review.

## Service Architecture

- **gateway_service** – normalizes access to LLM providers configured in `llm_router_config.yml`.
- **orchestrator_service** – drives the stage machine and contains LLM prompt helpers.
- **session_service** – manages WebSocket connections and stores turns in SQLite.
- **api_service** – FastAPI application exposing REST endpoints and the WebSocket interface.
- **interviewer_service**, **monitor_service**, **scoring_service** – pluggable modules for phrasing questions, inspecting answers, and computing scores.

All services live in `services/` and share a common runtime via `PYTHONPATH`.

## Running Locally

1. Configure the gateway:

```bash
cp services/gateway_service/.env.example services/gateway_service/.env
# edit the .env with keys for OPENAI, GEMINI, or a local provider
```

2. Build and start the stack:

```bash
docker-compose up --build
```

The compose file builds from `services/api_service/Dockerfile` and exposes the API on port **8003**.

## Test Frontend

Serve the static test page:

```bash
python -m http.server --directory test_frontend 3000
```

Open `http://localhost:3000` and supply a job description and resume to start an interview.

## API Endpoints

- WebSocket: `ws://localhost:8003/api/v1/ws/{session_id}`
- `GET /api/v1/sessions` – list stored sessions
- `GET /api/v1/sessions/{id}` – retrieve a session and its transcript
- `GET /api/v1/sessions/{id}/report` – download a PDF summary

## Logging & Tracing

`gateway_service.config.Settings` reads environment variables such as:

- `LOG_LEVEL` – `TRACE`, `DEBUG`, `INFO`, etc.
- `TRACE_CALLS` – log every function call/return
- `TRACE_MODULE_PREFIXES`, `TRACE_FILE_PATH_CONTAINS`, `TRACE_CONCISE` – narrow the scope and style of tracing

## Tests

Run the test suite with:

```bash
pytest
```
