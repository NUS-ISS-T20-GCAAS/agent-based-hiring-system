# Services

This directory contains the local backend service stack for the hiring system.

## Services Included

- `coordinator-agent`
- `resume-intake-agent`
- `screening-agent`
- `audit-agent`
- `ranking-agent`
- `postgres`

## Purpose

Use `services/docker-compose.yml` for local backend development and smoke testing without the frontend.

The coordinator is responsible for:

- receiving workflow requests
- parsing uploaded resume files
- calling agent services over HTTP
- persisting workflow state and artifacts to Postgres
- exposing read APIs for jobs, candidates, decisions, stats, health, and audit checks

## Current Backend Flow

The default coordinator path is:

1. bootstrap job, candidate, and workflow state
2. call resume intake
3. call screening
4. call audit
5. persist artifacts and update candidate state

Ranking is available as a separate manual step through `POST /jobs/{job_id}/rank`.

## Run Locally

```bash
docker compose -f services/docker-compose.yml up --build
```

Ports:

- coordinator: `8000`
- resume intake: `8001`
- screening: `8002`
- audit: `8003`
- ranking: `8004`
- postgres: `5432`

## Apply Migrations

```bash
sh /Users/isaactan/Projects/agent-based-hiring-system/db/migrate.sh /Users/isaactan/Projects/agent-based-hiring-system/services/docker-compose.yml
```

## Environment Variables

Relevant local environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `RESUME_INTAKE_AGENT_URL`
- `SCREENING_AGENT_URL`
- `RANKING_AGENT_URL`
- `AUDIT_AGENT_URL`
- `REQUEST_TIMEOUT`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

Behavior notes:

- Resume intake, screening, and audit use OpenAI when configured and fall back when unavailable.
- Ranking is heuristic only in the current codebase.
- Coordinator health checks only report whether the services are reachable; they do not stream live execution state.

## Upload Support

The coordinator accepts uploaded resumes in:

- `.txt`
- `.pdf`
- `.docx`

Parsing dependencies are installed in `coordinator-agent/requirements.txt`.

## Implemented Coordinator APIs

- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/rank`
- `GET /jobs/{job_id}/artifacts`
- `GET /candidates`
- `GET /candidates/{candidate_id}`
- `GET /candidates/{candidate_id}/decisions`
- `POST /candidates/upload`
- `POST /candidates/batch-upload`
- `GET /stats`
- `GET /agents/status`
- `GET /audit/bias-check`
- `GET /health`

## Notes

- This compose file is intended for development and local verification.
- The main workflow is synchronous.
- Agent-local shared memory exists, but Postgres-backed coordinator persistence is the primary system of record.
