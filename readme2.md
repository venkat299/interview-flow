# Repository Code Flow

The repository bundles several services that collaborate to run a conversational technical interview.

## Services

- `orchestrator_service` – stage machine and prompt helpers
- `session_service` – WebSocket manager and SQLite storage
- `gateway_service` – routes LLM requests to configured providers
- `interviewer_service`, `monitor_service`, `scoring_service` – optional modules for phrasing, diagnostics, and scoring
- `api_service` – FastAPI entry point exposing REST and WebSocket APIs

## Typical Flow

1. Client connects to `/api/v1/ws/{session_id}`.
2. `ConnectionManager` calls `llm_api.analyze_jd_resume` to build context.
3. `Orchestrator.loop` returns questions and transitions stages.
4. Answers are persisted and evaluated; monitoring and scoring can run per turn.
5. When no more questions remain, the session ends and can be retrieved via REST.

## Testing

Run:

```bash
pytest
```

to execute the available tests.
