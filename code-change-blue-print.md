# Code Change Blueprint: AI Interviewer Alignment

## Stage-Based Interview Flow
- The interview now runs through distinct stages (0–4) driven by a shared
  **Context Packet** capturing job description, resume details, skills, and
  notes.
- **Stage‑0** analyzes JD and resume to initialize the packet and timer.
- **Stage‑1** warm-up collects project context via overview and constraint
  questions.
- **Stage‑2** gathers evidence, skill hooks, and confidence ratings.
- **Stage‑3** verifies fundamentals for each hook.
- **Stage‑4** wraps up with strengths, risks, and follow-ups, consuming
  any remaining time.
- Final assessment aggregates **Depth of reasoning**, **Trade-off analysis**,
  **Fundamentals verified**, and **Clarity & precision** into a 10-point score
  reflected in the web UI and PDF report.

## Step 1 – Orchestrator Service
- **File**: `services/orchestrator_service/orchestrator.py`
  - `class Orchestrator`
    - `decide_next_action(state)` – choose ask / probe / switch topic / wrap.
    - `loop(state, answer)` – advance stage machine and return next question.
    - `record_turn(turn)` – hook for persistence (placeholder).
- **File**: `services/orchestrator_service/__init__.py`
  - Export `Orchestrator` for other services.

## Step 2 – WebSocket ConnectionManager
- **File**: `services/session_service/service.py`
  - `ConnectionManager` delegates stage flow to `Orchestrator`.
  - On `join_session`, runs stage‑0 `analyze_jd_resume` and seeds SQLite via `database.py`.
  - Emits `session_started`, `stage_changed`, `blueprint`, and `new_question` events.

## Step 3 – LLM Interviewer Module
- **File**: `services/interviewer_service/interviewer.py`
  - `class LLMInterviewer`
    - `next_question(context, item)` – placeholder paraphrasing.
    - `warm_start(resume)` – rapport prompt.
    - `wrap_up(state)` – closing prompt.
- **File**: `services/interviewer_service/__init__.py`

## Step 4 – LLM Monitor Module
- **File**: `services/monitor_service/monitor.py`
  - `class LLMMonitor`
    - `assess_turn(state, question, answer)` – placeholder diagnostics.
    - `suggest_next(state)` – placeholder recommendation.
- **File**: `services/monitor_service/__init__.py`

## Step 5 – Scoring Engine
- **File**: `services/scoring_service/scoring_engine.py`
  - `class ScoringEngine`
    - `aggregate(result, tests, rubric)` – placeholder sub‑scores.
    - `finalize(performance_log)` – placeholder final score.
- **File**: `services/scoring_service/__init__.py`

## Step 6 – LLM API Helpers
- **File**: `services/orchestrator_service/llm_api.py`
  - Stage helpers: `analyze_jd_resume`, `warmup_overview`, `warmup_constraint`, `evidence_skill_question`, `theory_check_question`, `wrap_up`.
  - REST helpers: `generate_next_question`, `create_interview_blueprint`, `evaluate_candidate_answer`.
  - Hooks: `on_question_selected`, `on_answer_scored` (wire Interviewer, Monitor, Scoring).

## Step 7 – Orchestration Loop Integration
- **File**: `services/orchestrator_service/orchestrator.py`
  - Implements the stage loop.
- **File**: `services/session_service/service.py`
  - Uses `Orchestrator.loop()` for each interaction.
- **File**: `services/api_service/app/main.py`
  - Exposes REST endpoints and the WebSocket endpoint.

## Step 8 – Performance & Modularity Notes
- Adopt async I/O in all service methods to maximize concurrency.
- Use dependency injection to swap LLM providers or sandboxes.
- Cache question bank & model prompts to reduce latency.
- Separate services enable horizontal scaling via containers or workers.
