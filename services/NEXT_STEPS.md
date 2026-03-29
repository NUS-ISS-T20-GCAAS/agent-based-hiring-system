# Next Step Plan

This roadmap is aligned to the current codebase state as of 2026-03-29.

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
- screening emits `needs_human_review` and `review_reasons`
- audit emits `review_required`, `risk_level`, and recommendations
- coordinator combines screening and audit signals into candidate review state
- candidate list and detail views render review-required information
- uploaded `.txt`, `.pdf`, and `.docx` resumes are parsed in the coordinator

Current gaps:

- `POST /jobs` is both a job endpoint and a workflow trigger, which makes the frontend sample-job flow misleading
- ranking is manual-only and its artifact is not persisted in Postgres
- the frontend still expects a WebSocket endpoint at `/ws`, but the backend does not expose one
- there is no delete candidate endpoint even though the frontend API layer defines a helper for it

## Recommended Order

### 1. Fix The Job-Creation Contract

Why first:

- The current frontend "Create Sample Job" flow calls `POST /jobs` with a dummy `resume_url`.
- That works against the endpoint's actual meaning and makes the product story harder to explain.

Implementation targets:

- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/schemas.py`
- `services/coordinator-agent/app/coordinator.py`
- `frontend/src/App.jsx`
- `frontend/src/components/Dashboard.jsx`

Acceptance criteria:

- the UI can create or edit a job without pretending to submit a candidate
- workflow-triggering endpoints are clearly separated from metadata-only job actions

### 2. Decide The Ranking Story

Why second:

- Ranking exists, but it sits outside the main flow and updates candidate state after the fact.
- That is workable for a demo, but the story should be explicit.

Two valid options:

- keep ranking manual and document it clearly, or
- move ranking into the default coordinator flow and persist its artifacts

Implementation targets:

- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/repository.py`
- `services/ranking-agent/app/agent.py`
- `services/coordinator-agent/tests/test_routes.py`

Acceptance criteria:

- ranking behavior is consistent with the intended demo narrative
- if ranking remains first-class, its outputs are persisted and explainable

### 3. Resolve The Live-Activity Mismatch

Why third:

- The frontend includes an Agent Activity tab and tries to connect to `/ws`.
- The backend currently has no matching route, so the "live updates" experience is misleading.

Two valid options:

- add a backend WebSocket or SSE stream, or
- remove the live-activity expectation from the UI

Implementation targets:

- `frontend/src/App.jsx`
- `frontend/src/components/AgentActivity.jsx`
- coordinator service routes if real streaming is added

Acceptance criteria:

- the UI no longer claims live activity that the backend cannot provide

### 4. Add Missing CRUD Cleanup Paths

Why fourth:

- The frontend API layer already has a `deleteCandidate` helper.
- There is no matching coordinator endpoint yet.

Implementation targets:

- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/repository.py`
- `frontend/src/services/api.js`

Acceptance criteria:

- candidate cleanup behavior is either implemented or removed from the frontend surface

### 5. Demo Verification Pass

Why fifth:

- By this point the product story should be coherent enough to validate end to end.

Minimum pass:

- create a job using the intended contract
- upload TXT, PDF, and DOCX resumes
- verify persisted intake, screening, and audit artifacts
- verify ranking behavior for one job
- verify review-required UI state

## Good Next Work After Demo-Critical Items

- better heuristic extraction quality
- stronger explanation formatting in the UI
- async queue or background job orchestration
- more complete fairness metrics and dashboards
- benchmark runs with representative resume samples
