# Services

This directory contains the local service stack for the hiring system.

## Services Included

- `coordinator-agent`
- `resume-intake-agent`
- `screening-agent`
- `postgres`

## Purpose

Use `/Users/isaactan/Projects/agent-based-hiring-system/services/docker-compose.yml` for local backend development and smoke testing without the frontend.

The coordinator is responsible for:

- receiving job requests
- calling agent services over HTTP
- persisting workflow state and artifacts to Postgres
- exposing read APIs for jobs, candidates, decisions, and stats

## Run Locally

```bash
docker compose -f services/docker-compose.yml up --build
```

## Apply Migrations

```bash
sh /Users/isaactan/Projects/agent-based-hiring-system/db/migrate.sh /Users/isaactan/Projects/agent-based-hiring-system/services/docker-compose.yml
```

## Environment Variables

Relevant local environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

If `OPENAI_API_KEY` is missing, the resume intake and screening agents still run using heuristic fallback logic.

## Implemented Flow

1. Coordinator accepts a request
2. Resume intake extracts candidate profile data
3. Screening scores the candidate
4. Coordinator saves jobs, candidates, workflow runs, and artifacts
5. Read APIs return DB-backed results

## Notes

- This compose file is for local development only
- It is not production-hardened
- Health endpoints expose whether the LLM path is enabled
