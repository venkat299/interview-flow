# Code Change Blueprint: AI Interviewer Alignment

## Step 1 – Introduce Orchestrator Service
- **File**: `services/orchestrator_service/orchestrator.py`
  - `class Orchestrator`
    - `run_session(session_ctx)` – own timer, topic coverage, and log dispatch.
    - `decide_next_action(state)` – choose ask / probe / switch topic / wrap.
    - `record_turn(turn)` – persist transcript and metadata.
- **File**: `services/orchestrator_service/__init__.py`
  - Export `Orchestrator` for other services.

## Step 2 – Refactor WebSocket ConnectionManager
- **File**: `services/ai_orchestration_service/session_service/service.py`
  - `ConnectionManager` delegates agenda & pacing to `Orchestrator` methods.
  - Replace inline question selection with orchestrator callbacks.
  - Expose hook `on_turn_complete(result)` for Monitor/Scoring modules.

## Step 3 – Create LLM Interviewer Module
- **File**: `services/interviewer_service/interviewer.py`
  - `class LLMInterviewer`
    - `next_question(context, item)` – paraphrase bank item and add micro‑empathy.
    - `warm_start(resume)` – rapport & diagnostic.
    - `wrap_up(state)` – final summary question.
- **File**: `services/interviewer_service/__init__.py`

## Step 4 – Create LLM Monitor Module
- **File**: `services/monitor_service/monitor.py`
  - `class LLMMonitor`
    - `assess_turn(state, question, answer)` – clarity, relevance, est_difficulty.
    - `suggest_next(state)` – recommended skill + level.
    - `time_nudge(state)` – enforce timebox, detect drift or hallucination.
- **File**: `services/monitor_service/__init__.py`

## Step 5 – Implement Scoring Engine
- **File**: `services/scoring_service/scoring_engine.py`
  - `class ScoringEngine`
    - `aggregate(result, tests, rubric)` – fuse signals, compute sub‑scores.
    - `finalize(performance_log)` – produce final score & justification.
- **File**: `services/scoring_service/__init__.py`

## Step 6 – Build Question Bank & Generator
- **File**: `services/question_service/question_bank.py`
  - `load_items()` – load seed bank with skill tags & tests.
  - `pick_item(state, monitor_diag)` – select next item via info gain & coverage.
- **File**: `services/question_service/generator.py`
  - `paraphrase(item, style)` – natural phrasing while preserving tags/tests.
- **File**: `services/question_service/__init__.py`

## Step 7 – Provide Execution Sandboxes
- **File**: `services/sandbox_service/code_runner.py`
  - `run_code(language, snippet, tests)` – exec with timeouts and resource caps.
- **File**: `services/sandbox_service/sql_runner.py`
  - `run_query(schema, data, query)` – isolated SQL evaluation.
- **File**: `services/sandbox_service/__init__.py`

## Step 8 – Implement Evidence Store
- **File**: `services/evidence_service/resume_parser.py`
  - `parse_resume(text)` – build claims graph nodes & edges.
- **File**: `services/evidence_service/artifact_ingest.py`
  - `ingest_repo(url)` – optional GitHub/portfolio ingestion.
- **File**: `services/evidence_service/__init__.py`

## Step 9 – Centralize Storage & Audit
- **File**: `services/storage_service/storage.py`
  - `save_transcript(session_id, turns)` – encrypted log storage.
  - `save_decision(state)` – persist prompts, model IDs, scoring decisions.
- **File**: `services/storage_service/__init__.py`

## Step 10 – Adaptivity & Difficulty Engine
- **File**: `services/adaptivity_service/ability_model.py`
  - `update(skill, response, time_taken)` – Bayesian/IRT posterior update.
  - `recommend_next()` – item selection signals for Question Bank.
- **File**: `services/adaptivity_service/__init__.py`

## Step 11 – Resume Claim Verification
- **File**: `services/verification_service/prober.py`
  - `select_claim(state)` – choose resume claim to probe.
  - `generate_probe(claim)` – specific, counterfactual, or micro‑task probe.
- **File**: `services/verification_service/__init__.py`

## Step 12 – Evaluation Pipeline Hooks
- **File**: `services/ai_orchestration_service/ai_orchestration.py`
  - Add orchestrator hooks `on_question_selected`, `on_answer_scored` to call Interviewer, Monitor, Scoring Engine.
- **File**: `services/ai_orchestration_service/app/main.py`
  - Expose REST/WebSocket routes that broker requests across new services.

## Step 13 – Question Quality Analytics
- **File**: `services/analytics_service/item_metrics.py`
  - `update_stats(item_id, score, time)` – difficulty & discrimination updates.
  - `record_feedback(item_id, clarity_rating)` – capture candidate feedback.
- **File**: `services/analytics_service/__init__.py`

## Step 14 – Safety, Fairness, Privacy Guardrails
- **File**: `services/guardrails_service/filters.py`
  - `check_question(text)` – block protected attributes / offensive tone.
  - `anonymize_logs(turn)` – remove PII before storage.
- **File**: `services/guardrails_service/__init__.py`

## Step 15 – Orchestration Loop Integration
- **File**: `services/orchestrator_service/orchestrator.py`
  - Add `loop()` implementing pseudocode: monitor → bank → interviewer → tools → scoring.
- **File**: `services/ai_orchestration_service/session_service/service.py`
  - Replace internal loop with call to `Orchestrator.loop()` for each session.

## Step 16 – Performance & Modularity Notes
- Adopt async I/O in all service methods to maximize concurrency.
- Use dependency injection to swap LLM providers or sandboxes.
- Cache question bank & model prompts to reduce latency.
- Separate services enable horizontal scaling via containers or workers.

