# Agentic Hiring System

An agent-based, explainable resume screening system built for scalable and auditable hiring decisions.

## Tech Stack
- Python 3.11
- FastAPI
- PostgreSQL
- OpenAI API
- Docker / Docker Compose

## Architecture Principles
- Custom agent framework (no LangChain / LangGraph)
- Stateless agents with shared memory
- Full decision traceability and audit logs
- Deterministic prompts and model configuration

## Supported Scope
- Text-based PDF resumes only
- Multiple predefined job roles
- Chat-style UI (future phase)
- Anonymized real-world resumes

## Local Development
```bash
docker compose up --build
