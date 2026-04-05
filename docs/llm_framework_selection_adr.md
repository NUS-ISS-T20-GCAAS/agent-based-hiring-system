# Architectural Decision Record (ADR): LLM Orchestration Framework Selection

## Background
The current agent-based hiring system uses a multi-agent architecture (Resume Intake, Skill Assessment, Screening, Audit, and Ranking) to process candidate resumes. These agents are currently orchestrated by a central **Coordinator Agent** using custom Python logic, FastAPI, and PostgreSQL for state management.

## Decision: Rejecting LangGraph and LangChain at Current Stage
We have evaluated the inclusion of **LangGraph** (for graph-based orchestration) and **LangChain** (for LLM abstraction) and decided to proceed with the existing **native Python + direct OpenAI SDK** implementation.

---

## 1. Why LangGraph is not needed
LangGraph is designed for complex, non-linear, cyclic agent graphs where "human-in-the-loop" and state checkpointing are primary requirements.

**Our Current Implementation Already Handles:**
- **Stateful Workflows:** `coordinator.py` uses a defined linear pipeline (Intake → Assessment → Screening → Audit) and persists the state in the `workflow_runs` and `workflow_queue` tables.
- **Persistence:** Postgres-backed `artifacts` and `candidate` updates provide robust state management and recovery.
- **Human-in-the-Loop:** We already have specialized flags (`needs_human_review`, `review_status`, `escalation_source`) integrated directly into our relational database.
- **Simplicity:** A fixed workflow is easier to debug, trace (via `handoff_trace.py`), and scale as a series of microservices without the overhead of a graph-execution engine.

**Verdict:** Transitioning to LangGraph would require refactoring ~800 lines of stable coordinator logic for marginal functional gain.

---

## 2. Why LangChain is not needed
LangChain provides high-level abstractions for prompts, document loaders, and output parsers.

**Our Current Implementation Already Handles:**
- **Prompting:** Each agent (e.g., `screening-agent/app/llm.py`) uses carefully tuned system prompts with bias guards and explicit JSON schemas.
- **Structured Output:** We use direct Pydantic models and regex-based JSON extraction (`_extract_json`), which are lightweight and highly reliable for our current use cases.
- **Document Processing:** PDF and DOCX parsing are handled directly via `pypdf` and `python-docx` in `resume_parser.py`, giving us fine-grained control over extraction quality.
- **Dependency Overhead:** LangChain would introduce a massive transitive dependency tree across all 6 microservices for functionality we have already built natively.

**Verdict:** LangChain would act as a "wrapper of a wrapper," adding complexity and potential breaking points without expanding our current LLM capabilities.

---

## Conclusion & Recommended Alternative: Langfuse
Instead of focusing on orchestration frameworks, we should prioritize **Observability**.

**The Gap:** While our current system traces *workflow-level* transitions (agent-to-agent), it lacks *LLM-level* tracing (prompt versions, token counts, cost monitoring, and sub-second latency per OpenAI call).

**The Solution:** We recommend adding **Langfuse**. This can be integrated by simply decorating or wrapping existing OpenAI client calls in each agent's `llm.py` without requiring any architectural changes or framework overhead.

---
*Created: 2026-04-06*
*Status: Accepted*
