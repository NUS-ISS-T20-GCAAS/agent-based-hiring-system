# Project Progress Tracker
**Project:** Agent-Based Hiring System for Scalable & Explainable Resume Screening
**Team:** Team 20
**Module:** GC Architecting AI Systems – Practice
**Last Updated:** 2026-03-21

---

## Overall Status

The project now has a working backend vertical slice:

1. Coordinator accepts job submissions
2. Resume intake agent parses candidate data
3. Screening agent scores qualification
4. Workflow state and artifacts are persisted in Postgres
5. DB-backed APIs expose jobs, candidates, decisions, stats, uploads, and artifact replay

OpenAI model hooks are implemented for the two active agent roles, but real model-backed execution still depends on configuring `OPENAI_API_KEY`.

---

## Phase 1 – Foundation (COMPLETED ✅)

### Architecture & Contracts
- [x] `BaseAgent` contract implemented
- [x] Standard artifact shape enforced
- [x] Correlation ID propagated across services
- [x] Shared memory replay implemented at agent-service level
- [x] Coordinator validates upstream artifact responses

### Inter-Service Communication
- [x] Coordinator dispatches work via HTTP
- [x] Resume intake runs as an independent service
- [x] Screening runs as an independent service
- [x] Health endpoints exposed for all active services

### Resilience & Observability
- [x] Retry logic with bounded attempts
- [x] Structured JSON logs
- [x] Failure events logged with correlation IDs
- [x] Artifact replay supported through `/jobs/{job_id}/artifacts`

---

## Phase 2 – Multi-Agent Vertical Slice (IMPLEMENTED ✅)

### Active Agents
- [x] Resume Intake Agent
- [x] Qualification Screening Agent
- [ ] Audit / Compliance Agent

### Coordinator Workflow
- [x] `resume-intake -> screening` orchestration
- [x] Workflow bootstrap and completion tracking
- [x] Candidate record creation during processing
- [x] Artifact persistence for each completed step

### Database & Persistence
- [x] Postgres migrations added
- [x] `jobs` table
- [x] `candidates` table
- [x] `workflow_runs` table
- [x] `artifacts` table
- [x] Read/write repository layer implemented

### Frontend-Facing APIs
- [x] `POST /jobs`
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
- [x] `GET /audit/bias-check` placeholder

### Testing & Verification
- [x] Coordinator route tests added
- [x] Coordinator orchestration tests added
- [x] Resume intake LLM/fallback tests added
- [x] Screening LLM/fallback tests added
- [x] End-to-end smoke test executed through the running service stack

---

## Phase 3 – Intelligence Refinement (IN PROGRESS 🚧)

### OpenAI-Backed Agent Roles
- [x] Resume intake model client added
- [x] Screening model client added
- [x] `OPENAI_MODEL` configuration added
- [x] `llm_enabled` health reporting added
- [ ] Real end-to-end run with production API key

### Quality Gaps
- [ ] Better PDF/DOCX/OCR parsing
- [ ] Improved candidate name extraction fallback
- [ ] Better job-skill extraction for heuristic screening
- [ ] Confidence scoring calibration

---

## Phase 4 – Planned Work

- [ ] Audit & Compliance Agent
- [ ] Bias detection implementation behind `/audit/bias-check`
- [ ] Human-in-the-loop escalation flow
- [ ] Async queue/event-driven execution if scale requires it
- [ ] Delete candidate endpoint and cleanup flows

---

## Notes

- The previous tracker understated the current backend progress.
- Persistence is now implemented in the coordinator workflow through Postgres.
- Agent-local shared memory still exists for per-service replay, but the system of record is now the database-backed coordinator flow.
- Real model reasoning is ready in code but inactive until OpenAI credentials are configured.
