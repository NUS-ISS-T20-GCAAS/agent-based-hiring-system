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

- ranking is manual-only and its artifact is not persisted in Postgres
- there is no delete candidate endpoint even though the frontend API layer defines a helper for it
- long-running uploads and workflow execution still run synchronously in the request/response path
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

### 1. Move Long-Running Work Off The Request Path

Why first:

- Large batch uploads can take long enough that synchronous request handling becomes brittle.
- The longer proxy timeout helps, but it does not remove the architecture bottleneck.

Implementation targets:

- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/repository.py`
- queue or worker infrastructure if introduced

Acceptance criteria:

- uploads and workflow execution no longer depend on one long HTTP request from the browser

### 2. Decide The Ranking Story

Why second:

- Ranking exists, but it sits outside the main flow and updates candidate state after the fact.
- That is workable for a demo, but the story should be explicit.

Implementation targets:

- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/repository.py`
- `services/ranking-agent/app/agent.py`
- `services/coordinator-agent/tests/test_routes.py`

Acceptance criteria:

- ranking behavior is consistent with the intended demo narrative
- if ranking remains first-class, its outputs are persisted and explainable

### 3. Add Cleanup Paths

Why third:

- The frontend API layer already has a `deleteCandidate` helper.
- There is no matching coordinator endpoint yet.

Implementation targets:

- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/repository.py`
- `frontend/src/services/api.js`

Acceptance criteria:

- candidate cleanup behavior is either implemented or removed from the frontend surface

### 4. Demo Verification Pass

Why fourth:

- By this point the product story should be coherent enough to validate end to end.

Minimum pass:

- create a job using the metadata-only job form
- upload TXT, PDF, and DOCX resumes
- upload a larger batch of 5 to 8 PDFs without proxy timeout failures
- verify at least one OpenAI-backed run if credentials are available
- verify persisted intake, screening, and audit artifacts
- verify ranking behavior for one job
- verify review-required UI state
- verify the live activity stream updates in the frontend

## Good Next Work After Demo-Critical Items

- better heuristic extraction quality
- stronger explanation formatting in the UI
- more complete fairness metrics and dashboards
- benchmark runs with representative resume samples
