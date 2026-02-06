# Project Progress Tracker  
**Project:** Agent-Based Hiring System for Scalable & Explainable Resume Screening  
**Team:** Team 20  
**Module:** GC Architecting AI Systems – Practice  
**Last Updated:** 2026-02-06  

---

## Phase 1 – Foundation (COMPLETED ✅)

### Objective
Establish a secure, traceable, and resilient foundation for a multi-agent hiring system, ensuring standardized agent contracts, explainability, and failure isolation before implementing domain logic.

---

## 1. Architecture & Core Contracts

### Agent Contract
- [x] `BaseAgent` abstract class implemented
- [x] Enforced `run()` lifecycle (logging, memory write, error capture)
- [x] Mandatory agent outputs:
  - payload
  - confidence
  - explanation
- [x] Correlation ID propagated across services

### Shared Memory
- [x] Append-only shared memory abstraction
- [x] Artifact versioning supported
- [x] Replay by `entity_id`
- [ ] Persistent storage (Postgres/Redis) – *Phase 3*

---

## 2. Inter-Service Communication

### Resume Intake Agent
- [x] Runs as an independent service
- [x] Exposes `/run`, `/artifacts/{entity_id}`, `/health`
- [x] Uses `BaseAgent` internally
- [x] Enforces `RunRequest` schema via Pydantic
- [x] Returns validated `Artifact` objects

### Coordinator Agent
- [x] Acts as orchestration layer only (no business logic)
- [x] Dispatches tasks via HTTP
- [x] Does not import agent code
- [x] Generates and propagates `correlation_id`

---

## 3. API Contracts & Validation

### Request Contracts
- [x] `RunRequest` schema enforced
- [x] Invalid requests rejected with `422 Unprocessable Entity`

### Response Contracts
- [x] `Artifact` schema enforced
- [x] Coordinator validates upstream responses
- [x] `/jobs/{id}/artifacts` returns validated artifact list

---

## 4. Resilience & Failure Handling

### Retry Strategy
- [x] Bounded retries (max 3 attempts)
- [x] Backoff between retries
- [x] Retry attempts logged with correlation_id
- [x] Retries limited to transient failures

### Failure Modes
- [x] Resume agent down → Coordinator returns `503`
- [x] Clean JSON error responses (no stack traces)
- [x] Failure events logged (`job_failed`, `agent_call_failed`)

---

## 5. Observability & Auditability

### Logging
- [x] Structured JSON logs
- [x] Correlation ID present in all logs
- [x] Agent lifecycle events logged:
  - job_received
  - agent_call_attempt
  - agent_call_failed
  - job_completed
- [x] Uvicorn access logs disabled to avoid noise

### Traceability
- [x] End-to-end replay via `/jobs/{id}/artifacts`
- [x] Artifact includes timestamps and agent metadata

---

## Phase 1 Verification Checklist (PASSED ✅)

| Test Case | Status |
|---------|--------|
| Happy path `/jobs` | ✅ |
| Artifact replay | ✅ |
| Invalid `/run` payload rejected | ✅ |
| Resume agent down → `/jobs` returns 503 | ✅ |
| Resume agent down → artifacts proxy returns 503 | ✅ |
| Retry attempts logged correctly | ✅ |

---

## Phase 2 – Individual Agents Development (UPCOMING 🚧)

### Planned Work
- [ ] Resume Intake: real parsing (PDF/DOC/OCR)
- [ ] Qualification Screening Agent (new service)
- [ ] Multi-agent orchestration (resume → qualification)
- [ ] Confidence scoring refinement

---

## Phase 3 – Coordination & Intelligence (PLANNED)

- [ ] Audit & Compliance Agent
- [ ] Bias detection hooks
- [ ] Persistent shared memory
- [ ] Human-in-the-loop escalation triggers

---

## Notes / Decisions Log
- Phase 1 prioritised correctness, traceability, and resilience over feature comp
