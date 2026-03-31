# Project Progress Tracker
**Project:** Agent-Based Hiring System for Scalable and Explainable Resume Screening
**Team:** Team 20
**Module:** GC Architecting AI Systems - Practice
**Last Updated:** 2026-03-31

---

## Overall Status

The repo now contains a working backend slice with five services:

1. coordinator
2. resume intake
3. screening
4. audit
5. ranking

The default persisted workflow is:

- coordinator bootstrap
- resume intake
- screening
- audit
- candidate persistence and review-state update

Job creation is now separated from workflow execution through a metadata-only `POST /jobs/create` path, and the frontend uses a real job-creation modal rather than a sample-job shortcut.

Ranking is implemented as a standalone manual step rather than part of the default pipeline.

OpenAI model hooks exist for resume intake, screening, and audit. Real model-backed execution still depends on `OPENAI_API_KEY`.

---

## Phase 1 - Foundation (COMPLETED)

### Architecture and Contracts
- [x] `BaseAgent` contract implemented across services
- [x] Standard artifact shape enforced
- [x] Correlation ID propagated across services
- [x] Shared memory replay implemented at agent-service level
- [x] Coordinator validates upstream artifact responses

### Inter-Service Communication
- [x] Coordinator dispatches work via HTTP
- [x] Resume intake runs as an independent service
- [x] Screening runs as an independent service
- [x] Audit runs as an independent service
- [x] Ranking runs as an independent service
- [x] Health endpoints exposed for all current services

### Resilience and Observability
- [x] Retry logic with bounded attempts for coordinator agent calls
- [x] Structured JSON logs
- [x] Failure events logged with correlation IDs
- [x] Artifact replay supported through `GET /jobs/{job_id}/artifacts`

---

## Phase 2 - Multi-Agent Vertical Slice (IMPLEMENTED)

### Active Agents
- [x] Resume Intake Agent
- [x] Qualification Screening Agent
- [x] Audit Agent
- [x] Ranking Agent

### Coordinator Workflow
- [x] `resume-intake -> screening -> audit` orchestration
- [x] Workflow bootstrap and completion tracking
- [x] Candidate record creation during processing
- [x] Metadata-only job creation via `POST /jobs/create`
- [x] Artifact persistence for intake, screening, and audit
- [x] Coordinator-level human review state derived from screening and audit
- [x] Review-required state exposed through candidate read APIs
- [ ] Ranking integrated into the default pipeline
- [ ] Ranking artifact persisted in Postgres

### Database and Persistence
- [x] Postgres migrations added
- [x] `jobs` table
- [x] `candidates` table
- [x] `workflow_runs` table
- [x] `artifacts` table
- [x] `jobs.job_requirements` JSONB field
- [x] `candidates.needs_human_review`
- [x] `candidates.review_status`
- [x] `candidates.review_reasons`
- [x] `candidates.escalation_source`
- [x] Read/write repository layer implemented

### Frontend-Facing APIs
- [x] `POST /jobs`
- [x] `POST /jobs/create`
- [x] `GET /jobs`
- [x] `GET /jobs/{job_id}`
- [x] `POST /jobs/{job_id}/rank`
- [x] `GET /jobs/{job_id}/artifacts`
- [x] `GET /candidates`
- [x] `GET /candidates/{candidate_id}`
- [x] `GET /candidates/{candidate_id}/decisions`
- [x] `POST /candidates/upload`
- [x] `POST /candidates/batch-upload`
- [x] `GET /stats`
- [x] `GET /agents/status`
- [x] `GET /audit/bias-check`

### Testing Surface
- [x] Coordinator route tests
- [x] Coordinator orchestration tests
- [x] Resume parsing tests for TXT, PDF, and DOCX upload paths
- [x] Resume intake LLM and fallback tests
- [x] Screening LLM and fallback tests
- [x] Audit agent LLM and fallback tests
- [x] Ranking agent tests

---

## Phase 3 - Intelligence Refinement (IN PROGRESS)

### OpenAI-Backed Agent Roles
- [x] Resume intake model client added
- [x] Screening model client added
- [x] Audit model client added
- [x] `OPENAI_MODEL` configuration added
- [x] `llm_enabled` health reporting added where applicable
- [ ] Real end-to-end run with production API key

### Quality Gaps
- [ ] Better candidate/entity extraction heuristics in fallback paths
- [ ] Better job-skill extraction from free-text descriptions
- [ ] Confidence calibration across screening and audit
- [ ] Stronger explanation rendering in the frontend detail views

---

## Phase 4 - Demo-Critical Work (NEXT)

- [ ] Decide whether ranking should be manual-only or part of the main workflow
- [ ] Persist ranking artifacts if ranking remains a first-class step
- [ ] Add delete candidate endpoint and cleanup flow, or remove the unused frontend helper
- [ ] Move long-running uploads/workflows to background jobs or queue-based orchestration
- [ ] Run a demo-readiness verification pass against the composed stack

## Phase 5 - Remaining Nice-To-Haves

- [ ] Improve heuristic extraction and explanations where still weak
- [ ] Expand dashboard support for richer fairness and workflow metrics
- [ ] Add async queue or event-driven execution if scale requires it

---

## Notes

- PDF and DOCX extraction are now implemented in the coordinator via `pypdf` and `python-docx`.
- Screening review flags and audit review flags are already combined into coordinator-level candidate review state.
- The frontend shows review state in list and detail views.
- The coordinator exposes a live WebSocket endpoint at `/ws` and broadcasts agent activity and candidate updates through a shared event hub.
- The frontend connects to that live activity stream.
- Batch upload requests can take longer for larger resume sets, so the frontend proxy timeout and body-size limits were increased to avoid premature 504s during long-running uploads.
