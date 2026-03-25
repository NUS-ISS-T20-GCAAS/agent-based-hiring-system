# Next Step Plan

This roadmap is aligned to the project proposal and the current codebase state as of 2026-03-25.

## Demo Goal

Minimum believable finish line:

- working intake
- working screening
- working audit
- visible explanations in the UI
- reliable PDF/DOCX resume uploads
- review and escalation path for uncertain or risky outcomes

## Current State

Already working:

- coordinator persists jobs, candidates, workflow runs, and artifacts
- resume intake and screening run as independent services
- screening already emits `needs_human_review` and `review_reasons`
- audit agent exists as an independent service with LLM and heuristic fallback
- candidate detail modal already renders a decision trail

Still missing for the demo:

- no coordinator-level rule combines screening review flags and audit review flags
- frontend does not show review-required or escalation state clearly
- upload parsing still uses raw byte decoding, which is too weak for PDF/DOCX reliability
- benchmark and smoke-test coverage still need a final demo-readiness pass

## Recommended Order

### 1. Audit Integration

Status:

- completed in the current slice

Why first:

- It closes the largest proposal gap with the least UI disruption.
- It unlocks real audit artifacts, audit-backed explanations, and a credible fairness story.

Implementation targets:

- `services/coordinator-agent/app/config.py`
- `services/coordinator-agent/app/coordinator.py`
- `services/coordinator-agent/app/routes.py`
- `services/coordinator-agent/app/repository.py`
- `services/coordinator-agent/tests/test_coordinator.py`
- `services/coordinator-agent/tests/test_routes.py`

Acceptance criteria:

- coordinator calls `audit-agent` after screening
- audit artifact is persisted in `artifacts`
- `GET /jobs/{job_id}/artifacts` includes audit output
- `GET /audit/bias-check` is backed by the audit agent instead of placeholder logic

### 2. Human Review / Escalation

Why second:

- The review path should be defined after both screening and audit signals are available.
- This is the feature that turns separate agent outputs into accountable workflow behavior.

Implementation targets:

- database migration for review fields on `candidates` and possibly `workflow_runs`
- `services/coordinator-agent/app/repository.py`
- `services/coordinator-agent/app/routes.py`
- `frontend/src/services/api.js`
- `frontend/src/components/Candidates.jsx`
- `frontend/src/components/CandidateDetailModal.jsx`

Coordinator rule:

- `needs_human_review = screening.payload.needs_human_review OR audit.payload.review_required`

Recommended stored fields:

- `needs_human_review`
- `review_reasons`
- `review_status`
- `escalation_source`

Acceptance criteria:

- candidate records expose whether human review is required
- UI shows review-required or escalation status
- UI shows the reasons coming from screening and audit

### 3. Resume Parsing Upgrade

Why third:

- This is the highest demo-risk item, but it is easier to validate after the workflow path is complete.
- Better parsing also improves downstream screening and explainability quality.

Implementation targets:

- move file extraction out of the coordinator route helper and into a dedicated parser utility
- add PDF extraction library support
- add DOCX extraction library support
- keep plain text fallback for `.txt`

Suggested libraries:

- `pypdf` for PDF text extraction
- `python-docx` for DOCX extraction

Acceptance criteria:

- uploaded PDF resumes produce readable extracted text
- uploaded DOCX resumes produce readable extracted text
- extraction failures return clear errors instead of empty garbage text

### 4. UI Explainability Completion

Why fourth:

- The frontend already has a strong place to display this once real audit and review data exist.

Implementation targets:

- `frontend/src/components/CandidateDetailModal.jsx`
- `frontend/src/components/Candidates.jsx`
- `frontend/src/components/Dashboard.jsx`

Acceptance criteria:

- audit result is visible in candidate details
- decision trail clearly distinguishes intake, screening, and audit
- review-required state is visible in both list and detail views

### 5. Benchmark and Testing Pass

Why fifth:

- This should validate the integrated path, not the partial one.

Minimum pass:

- coordinator tests cover intake -> screening -> audit flow
- route tests cover audit-backed endpoints
- upload tests cover PDF/DOCX extraction paths
- one end-to-end smoke run confirms the demo narrative

## Good Next Work After Demo-Critical Items

- standalone ranking / recommendation agent
- better heuristic quality for skill extraction
- stronger candidate name extraction
- confidence calibration
- auto-trigger audit after each screening batch or candidate completion
- dashboard cards for fairness metrics and stage-by-stage status

## Suggested First PR

Suggested next PR scope:

- add coordinator-level `needs_human_review`
- persist review reasons and escalation source
- expose review-required state to the frontend
- surface escalation badges in candidate list and detail view

This is now the smallest slice that materially improves the demo story after audit integration.
