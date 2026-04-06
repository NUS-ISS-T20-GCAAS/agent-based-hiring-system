# Services

This directory contains the local backend service stack for the hiring system.

## Services Included

- `coordinator-agent`
- `resume-intake-agent`
- `screening-agent`
- `skill-assessment-agent`
- `audit-agent`
- `ranking-agent`
- `postgres`
- `redis` (Celery broker)
- `celery-worker` (Async task worker)

## Purpose

Use `services/docker-compose.yml` for local backend development and smoke testing without the frontend.

The coordinator is responsible for:

- receiving workflow requests
- parsing uploaded resume files
- dispatching asynchronous workflows to Celery via Redis
- calling agent services over HTTP from the Celery worker
- persisting workflow state and artifacts to Postgres
- exposing read APIs for jobs, candidates, decisions, stats, health, and audit checks

## Current Backend Flow

The default coordinator path is:

1. accept upload requests and parse TXT, PDF, or DOCX resumes
2. dispatch workflow task to Celery via Redis
3. Celery worker process picks up the job
4. bootstrap job, candidate, and workflow state
5. call resume intake
6. call skill assessment
7. call screening
8. call audit
9. persist artifacts and update candidate state

Ranking is available as a separate manual step through `POST /jobs/{job_id}/rank`.

## Run Locally

```bash
docker compose -f services/docker-compose.yml up --build
```

On startup, the compose stack runs `db/init_db.sql` and all files in `db/migrations/` through a dedicated migration step before the coordinator starts.

Ports:

- coordinator: `8000`
- resume intake: `8001`
- screening: `8002`
- skill assessment: `8005`
- audit: `8003`
- ranking: `8004`
- postgres: `5432`
- redis: `6379`

## Apply Migrations

```bash
sh db/migrate.sh services/docker-compose.yml
```

Use this when you want to re-apply the schema manually against an already-running local database.

## Environment Variables

Relevant local environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `RESUME_INTAKE_AGENT_URL`
- `SCREENING_AGENT_URL`
- `SKILL_ASSESSMENT_AGENT_URL`
- `RANKING_AGENT_URL`
- `AUDIT_AGENT_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `REQUEST_TIMEOUT`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

Behavior notes:

- Coordinator can generate a persisted `workflow_orchestration_plan` artifact and pass that plan into downstream stages when `OPENAI_API_KEY` is configured.
- Resume intake, skill assessment, screening, and audit use OpenAI when configured and fall back when unavailable.
- Skill assessment focuses on competency/gap analysis rather than pass/fail decisions.
- Ranking is heuristic only in the current codebase.
- Coordinator health and `/queue/status` endpoints now report Celery broker connectivity and worker task statistics (active/reserved/scheduled) when Redis is reachable.

## Upload Support

The coordinator accepts uploaded resumes in:

- `.txt`
- `.pdf`
- `.docx`

Parsing dependencies are installed in `coordinator-agent/requirements.txt`.

## Implemented Coordinator APIs

- `POST /jobs`
- `POST /jobs/create`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/rank`
- `GET /jobs/{job_id}/artifacts`
- `GET /jobs/{job_id}/handoffs`
- `GET /candidates`
- `GET /candidates/{candidate_id}`
- `DELETE /candidates/{candidate_id}`
- `GET /candidates/{candidate_id}/decisions`
- `POST /candidates/upload`
- `POST /candidates/batch-upload`
- `GET /stats`
- `GET /agents/status`
- `GET /audit/bias-check`
- `GET /health`
- WebSocket `/ws`

## Notes

- This compose file is intended for development and local verification.
- Upload-triggered workflows are dispatched to Redis and processed asynchronously by the Celery worker process.
- Cross-process live activity updates are bridged using Redis PubSub.
- Agent-local shared memory exists, but Postgres-backed coordinator persistence is the primary system of record.
