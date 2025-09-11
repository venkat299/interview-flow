# Code Change Blueprint

Guide for extending the stage‑based AI interviewer.

## Stage Overview

0. **Analysis** – parse job description and resume, seed timers.
1. **Warm‑up** – gather project overview and constraints.
2. **Evidence** – collect examples and confidence ratings.
3. **Theory** – probe fundamentals for each skill hook.
4. **Wrap‑up** – summarize strengths, risks, and follow‑ups.

The final report aggregates reasoning depth, trade‑offs, fundamentals verified, and clarity into a 10‑point score.

## Key Modules

- **Orchestrator** (`services/orchestrator_service/orchestrator.py`)
  - `decide_next_action`, `loop`, `record_turn`
- **ConnectionManager** (`services/session_service/service.py`)
  - runs Stage‑0 and delegates all turns to the orchestrator
- **LLM Interviewer** (`services/interviewer_service/interviewer.py`)
  - `next_question`, `warm_start`, `wrap_up`
- **LLM Monitor** (`services/monitor_service/monitor.py`)
  - `assess_turn`, `suggest_next`
- **ScoringEngine** (`services/scoring_service/scoring_engine.py`)
  - `aggregate`, `finalize`
- **LLM Helpers** (`services/orchestrator_service/llm_api.py`)
  - Stage helpers such as `analyze_jd_resume`, `warmup_overview`, `evidence_skill_question`, `theory_check_question`, `wrap_up`
  - REST helpers `generate_next_question`, `create_interview_blueprint`, `evaluate_candidate_answer`

## Development Notes

- Keep service functions async to maximize concurrency.
- Use dependency injection to swap LLM providers or sandboxes.
- Cache prompts or question banks to reduce latency.
- Services can scale horizontally in separate containers.
