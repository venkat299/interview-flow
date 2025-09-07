# Repository Code Flow

This project implements an AI-driven interview platform using FastAPI and modular services.

## Backend Services
- **Orchestrator**: Drives session pacing, selects actions, and logs turns.
- **Interviewer**: Uses an LLM to phrase questions conversationally.
- **Monitor**: Evaluates each turn for clarity and difficulty while tracking skill estimates.
- **Scoring Engine**: Aggregates test outcomes and rubric scores into final results.
- **Question Service**: Provides seed items and paraphrases stems for natural prompts.
- **Sandbox Service**: Executes code and SQL snippets in isolated environments.
- **Evidence & Verification**: Parses resumes and probes claims for truthfulness.
- **Analytics & Guardrails**: Collects item metrics and filters unsafe content.
- **Storage**: Persists transcripts, decisions, and reports.

## API Flow
1. Clients initiate sessions via REST or WebSocket.
2. The orchestrator builds an interview blueprint and dispatches the first question.
3. Candidate responses are evaluated by sandboxes and scoring services.
4. The monitor updates ability estimates and suggests the next topic.
5. Sessions end with a summary score and stored transcript.

## Frontend
A simple test client connects over WebSocket, displays questions, and shows final summaries.

## Testing
Run `pytest` to execute the integration test covering the end-to-end flow.
