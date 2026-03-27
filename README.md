# Agent-Based Hiring System

An explainable hiring workflow built as cooperating services:

- `frontend` for the UI
- `coordinator-agent` for orchestration
- `resume-intake-agent` for profile extraction
- `screening-agent` for qualification scoring
- `postgres` for workflow and artifact persistence
- `terraform` for infrastructure deployment

## Current Status

The current vertical slice is working end-to-end for text-based resume processing:

1. Submit a job or uploaded resume to the coordinator
2. Coordinator calls resume intake
3. Resume intake returns structured candidate data
4. Coordinator calls screening
5. Screening returns a qualification result
6. Jobs, candidates, workflow runs, and artifacts are persisted in Postgres
7. Frontend-facing read APIs return DB-backed data

### For infrastructure progress
1. Finished EKS cluster with Fargate and managed node group
2. Hosted frontend on EKS with ALB
   - DNS name (ELB): `http://a237b86696f4a4559a776297a3ab85a9-173539850.ap-southeast-1.elb.amazonaws.com/`
3. Linked frontend to coordinator-agent in EKS
4. Setup ECR repositories
   - `arn:aws:ecr:ap-southeast-1:693517970860:repository/hiring-system/coordinator-agent`
   - `arn:aws:ecr:ap-southeast-1:693517970860:repository/hiring-system/resume-intake-agent`
   - `arn:aws:ecr:ap-southeast-1:693517970860:repository/hiring-system/screening-agent`
   - `arn:aws:ecr:ap-southeast-1:693517970860:repository/hiring-system/frontend`
5. Updated frontend's pipeline to push to ECR and deploy to EKS, merged frontend-build.yml into frontend-deploy.yml to automate the build and deploy process
6. Setup RDS PostgreSQL 15 (Login AWS Console -> RDS -> Databases -> hiring-system-dev-postgres for endpoint and credentials)

#### Pending infrastructure tasks
- [ ] Domain name and SSL certificate
- [ ] Update services' pipeline to automate the build and deploy process in a single workflow
- [ ] Deploy coordinator-agent, resume-intake-agent, and screening-agent to EKS
- [ ] Import database schema to hiring-system-dev-postgres
- [ ] Update coordinator-agent, resume-intake-agent, and screening-agent to use RDS PostgreSQL 15

## Tech Stack

- Python 3.11
- FastAPI
- PostgreSQL 15
- Docker / Docker Compose
- Kubernetes 1.32
- OpenAI API (optional at runtime)

## Architecture Notes

- Agents follow a common contract with `payload`, `confidence`, and `explanation`
- The coordinator handles orchestration and persistence
- Artifacts are replayable through the coordinator
- Agent services can use OpenAI when `OPENAI_API_KEY` is configured
- If no key is configured, resume intake and screening fall back to heuristic logic

## Implemented APIs

The coordinator currently exposes:

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

## OpenAI Integration

Two agent roles are wired for model-backed execution:

- Resume intake:
  - `/Users/isaactan/Projects/agent-based-hiring-system/services/resume-intake-agent/app/llm.py`
  - `/Users/isaactan/Projects/agent-based-hiring-system/services/resume-intake-agent/app/agent.py`
- Qualification screening:
  - `/Users/isaactan/Projects/agent-based-hiring-system/services/screening-agent/app/llm.py`
  - `/Users/isaactan/Projects/agent-based-hiring-system/services/screening-agent/app/agent.py`

The model and key are configured through:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-4o-mini`)

Health endpoints expose whether model-backed execution is active through `llm_enabled`.

## Local Development

### Start the full stack

```bash
docker compose -f infra/docker-compose.yml up --build
```

### Start the services-only stack

```bash
docker compose -f services/docker-compose.yml up --build
```

### Apply database migrations

```bash
sh db/migrate.sh infra/docker-compose.yml
```

Or for the services-only compose file:

```bash
sh db/migrate.sh services/docker-compose.yml
```

### Helpful Make targets

```bash
make build-all
make compose-build-all
make migrate-db
make migrate-db-services
```

## Current Gaps

- Resume parsing is still basic for uploaded files
- Proper PDF/DOCX/OCR extraction is not implemented yet
- Screening fallback scoring needs refinement
- Bias/audit functionality is still a placeholder
- Real model-backed end-to-end runs require `OPENAI_API_KEY`
