# Next Step Plan

This roadmap is aligned to the current codebase state as of 2026-03-31.

## Demo Goal

Minimum believable finish line:

- reliable job creation and resume upload flow
- persisted intake, screening, and audit artifacts
- visible explanations and review state in the UI
- optional ranking that is easy to explain
- clear story for health and live activity

## Current State

Already working:

- coordinator persists jobs, candidates, workflow runs, and artifacts
- resume intake, screening, audit, and ranking run as independent services
- job creation is metadata-only through `POST /jobs/create`
- screening emits `needs_human_review` and `review_reasons`
- audit emits `review_required`, `risk_level`, and recommendations
- coordinator combines screening and audit signals into candidate review state
- candidate list and detail views render review-required information
- uploaded `.txt`, `.pdf`, and `.docx` resumes are parsed in the coordinator
- the coordinator exposes a live WebSocket endpoint at `/ws`
- the frontend connects to the live activity stream
- the frontend proxy has longer read/send timeouts and a larger upload body limit for batch resume uploads

Current gaps:

- ranking is manual-only and should remain a separate layer from screening/audit decisions
- uploads now enqueue into a Postgres-backed worker, but there is not yet a separate multi-process queue stack such as Redis/Celery
- heuristic extraction and explanations still have room to improve

## Package To Add

Recommended shortlist, ranked by expected project value:

1. `langgraph`
   Best fit for showing real multi-agent orchestration, stateful workflows, checkpoints, and human-in-the-loop design.

2. `redis` + `celery`
   Best fit for solving the current synchronous upload bottleneck through background jobs, task queues, and lightweight caching.

3. `langfuse`
   Best fit for demo and report visibility through tracing, prompt/version tracking, and LLM observability.

4. `langchain`
   Strong ecosystem choice for prompts, retrievers, document processing, tools, and integration glue if the project needs a broader LLM framework.

5. `instructor`
   High practical value for structured resume extraction into validated Pydantic models with cleaner OpenAI response handling.

6. `qdrant-client`
   Useful if semantic search or vector-based resume-to-job matching is added later.

7. `guardrails-ai`
   Useful for output validation, safety constraints, and stronger governance around generated screening or extraction results.

8. `pydantic-ai`
   Good Python-native option for typed agent workflows if the team prefers a lighter abstraction than LangChain.

Best packages to prioritize:

- easiest practical win: `instructor`
- most impressive for demo/story: `langgraph`
- best architectural fix for the current system: `redis` + `celery`
- best visibility and evaluation add-on: `langfuse`

## Recommended Order

### 1. Demo Verification Pass

Why first:

- The biggest demo-critical engineering gaps are now closed, so the next value is validating the whole story end to end.

Implementation targets:

- composed local stack and deployed stack
- representative TXT, PDF, and DOCX resumes
- ranking, review-state, and live activity screens

Acceptance criteria:

- upload queue drains correctly through the worker
- live activity updates appear while queued workflows run
- persisted artifacts and review state are visible in the UI

### 2. Heuristic And Explanation Polish

Why second:

- The baseline pipeline works, but fallback extraction and explanation quality can still look rough during demos.

Implementation targets:

- `services/resume-intake-agent/app/agent.py`
- `services/screening-agent/app/agent.py`
- `services/audit-agent/app/agent.py`
- `services/coordinator-agent/app/routes.py`
- frontend explanation rendering components

Acceptance criteria:

- extracted candidate profiles look more complete in fallback mode
- explanations are easier to read in list/detail views

### 3. Bigger Queue Upgrade

Why third:

- The current Postgres-backed worker is good for demo durability, but not the final scaling story.

Implementation targets:

- queue infrastructure package choice
- coordinator worker deployment model
- retry/dead-letter strategy

Acceptance criteria:

- queue processing can survive coordinator restarts and scale beyond one in-process worker

## Good Next Work After Demo-Critical Items

- better heuristic extraction quality
- stronger explanation formatting in the UI
- more complete fairness metrics and dashboards
- benchmark runs with representative resume samples
