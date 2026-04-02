# Project Progress Tracker
**Project:** Agent-Based Hiring System for Scalable and Explainable Resume Screening
**Team:** Team 20
**Module:** GC Architecting AI Systems - Practice
**Last Updated:** 2026-04-01

---

## Overall Status

The repo now contains a working backend slice with six services:

1. coordinator
2. resume intake
3. skill assessment
4. screening
5. audit
6. ranking

The default persisted workflow is:

- coordinator bootstrap
- resume intake
- skill assessment
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
- [x] Skill assessment runs as an independent service
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
- [x] Skill Assessment Agent
- [x] Qualification Screening Agent
- [x] Audit Agent
- [x] Ranking Agent
- [x] Ranking agent now emits recommendation-oriented ranking factors and action suggestions

### Coordinator Workflow
- [x] `resume-intake -> skill-assessment -> screening -> audit` orchestration
- [x] Workflow bootstrap and completion tracking
- [x] Candidate record creation during processing
- [x] Metadata-only job creation via `POST /jobs/create`
- [x] Artifact persistence for intake, skill assessment, screening, and audit
- [x] Coordinator-level human review state derived from screening and audit
- [x] Review-required state exposed through candidate read APIs
- [ ] Ranking integrated into the default pipeline
- [x] Manual ranking metadata persisted per candidate

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
- [x] Skill assessment agent tests

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

- [x] Decide that ranking stays manual-only rather than part of the default workflow
- [x] Persist manual ranking state without overwriting screening/audit outcomes
- [x] Add delete candidate endpoint and cleanup flow
- [x] Move long-running uploads/workflows to a Postgres-backed queue worker
- [ ] Run a demo-readiness verification pass against the composed stack

## Phase 5 - Remaining Nice-To-Haves

- [ ] Improve heuristic extraction and explanations where still weak
- [ ] Expand dashboard support for richer fairness and workflow metrics
- [ ] Add multi-process queue infrastructure such as Redis/Celery if scale requires it

---

## Notes

- PDF and DOCX extraction are now implemented in the coordinator via `pypdf` and `python-docx`.
- Screening review flags and audit review flags are already combined into coordinator-level candidate review state.
- The frontend shows review state in list and detail views.
- The frontend now shows manual ranking separately from screening and audit outcomes.
- The coordinator exposes a live WebSocket endpoint at `/ws` and broadcasts agent activity and candidate updates through a shared event hub.
- The frontend connects to that live activity stream.
- Upload routes now enqueue parsed workflow requests in Postgres and a coordinator worker claims them asynchronously.
- Batch upload requests can still take longer for larger resume sets overall, but the browser request no longer needs to stay open until every workflow finishes.
