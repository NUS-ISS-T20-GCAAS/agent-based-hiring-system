# Agent-Based Hiring System

An explainable hiring workflow built as cooperating services:

- `frontend` for the recruiter dashboard
- `coordinator-agent` for orchestration and persistence
- `resume-intake-agent` for structured resume extraction
- `screening-agent` for qualification scoring and review flags
- `audit-agent` for bias and compliance checks
- `ranking-agent` for manual re-ranking of candidates in a job
- `postgres` for jobs, candidates, workflow runs, and artifacts
- `infra/terraform` for AWS infrastructure definitions

## Current Status

The current codebase supports a working synchronous backend flow:

1. Create a job through the metadata-only `POST /jobs/create` form, or upload resumes to an existing job with `POST /candidates/upload` or `POST /candidates/batch-upload`.
2. The coordinator upserts job metadata, creates a candidate for each uploaded resume, and opens a workflow run.
3. The coordinator calls `resume-intake-agent`.
4. The coordinator calls `screening-agent`.
5. The coordinator calls `audit-agent`.
6. The coordinator persists artifacts from each completed step in Postgres.
7. The coordinator updates candidate scores, recommendation, and human-review state.
8. The frontend reads jobs, candidates, stats, decision history, audit output, and live activity updates from coordinator APIs.

Ranking exists as a separate service, but it is not part of the default intake -> screening -> audit pipeline. It is still triggered on demand through `POST /jobs/{job_id}/rank`.


### For infrastructure progress (AI please don't delete this section as it is maintained by other human)
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

#### Pending infrastructure tasks (AI please don't delete this section as it is maintained by other human)
- [ ] Domain name and SSL certificate
- [x] Update services' pipeline to automate the build and deploy process in a single workflow
- [x] Deploy coordinator-agent, resume-intake-agent, and screening-agent to EKS
- [x] Pending deployment for audit-agent and ranking-agent
- [x] Import database schema to hiring-system-dev-postgres
- [x] Update coordinator-agent, resume-intake-agent, and screening-agent to use RDS PostgreSQL 15 (It seems DB connected in the frontend)

## AWS Infrastructure Cost Optimization

To minimize AWS costs when the environment is not in active use (saving ~$3.50/day or ~$105/month), we have automated the process of tearing down the most expensive non-persistent resources while keeping the database and container images intact.

### Cost-Saving Workflow (AI please don't delete this section as it is required attention from others)
1.  Go to the **Actions** tab in GitHub.
2.  Select the **"Terraform Manage (Destroy / Recreate) for cost saving"** workflow.
3.  Click **Run workflow**.
4.  **To Destroy (Save Cost):**
    *   Set **Action** to `destroy`.
    *   Type `yes` in the **confirm** field.
    *   This will tear down the EKS Cluster (Control Plane + Nodes) and the NAT Gateway.
    *   **Kept resources:** VPC, Subnets, RDS (Database), ECR (Images). Current service image tags are automatically captured and saved.
5.  **To Recreate (Start Working):**
    *   Set **Action** to `recreate`.
    *   This will bring back the EKS Cluster and NAT Gateway, and automatically re-deploy all 6 services using their previously captured image tags.

> [!IMPORTANT]
> Always use this workflow instead of a full `terraform destroy` to ensure your database data and network configuration are preserved!

## Tech Stack

- Python 3.11
- FastAPI
- PostgreSQL 15
- React 18 + Vite + Tailwind CSS
- Docker / Docker Compose
- Terraform for AWS infrastructure
- OpenAI API for model-backed agent execution when configured

## Architecture Notes

- Agents share a common artifact contract with `payload`, `confidence`, and `explanation`.
- The coordinator is the system of record for workflow orchestration and persistence.
- Agent-local shared memory is still present for service-level replay and diagnostics.
- Resume intake, screening, and audit attempt OpenAI-backed execution when `OPENAI_API_KEY` is configured.
- Ranking is currently heuristic only.
- Screening and audit can jointly escalate candidates for human review.

## Implemented Coordinator APIs

The coordinator currently exposes:

- `POST /jobs`
- `POST /jobs/create`
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
- WebSocket `/ws`

The frontend calls these through an `/api/` proxy when running behind the bundled Nginx config.

## Data Stored In Postgres

The coordinator persists workflow state across:

- `jobs`
- `candidates`
- `workflow_runs`
- `artifacts`

The `jobs` table also stores `job_requirements`, and the `candidates` table stores review state:

- `needs_human_review`
- `review_status`
- `review_reasons`
- `escalation_source`

## Resume Upload Support

Uploaded resumes are parsed in the coordinator before the workflow begins.

Supported file types:

- `.txt`
- `.pdf`
- `.docx`

Implementation notes:

- TXT files are decoded directly.
- PDF extraction uses `pypdf`.
- DOCX extraction uses `python-docx`.
- Unsupported file types return HTTP `415`.

## OpenAI Integration

Model-backed execution is currently wired for:

- `resume-intake-agent`
- `screening-agent`
- `audit-agent`

Configuration:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` with default `gpt-4o-mini`

Health endpoints expose `llm_enabled` for the agents that support model execution.

## Local Development

### Start the full stack

```bash
docker compose -f infra/docker-compose.yml up --build
```

On startup, the compose stack now runs `db/init_db.sql` and all files in `db/migrations/` through a dedicated migration step before the coordinator starts.

This starts:

- frontend on `http://localhost:3000`
- coordinator on `http://localhost:8000`
- resume intake on `http://localhost:8001`
- screening on `http://localhost:8002`
- audit on `http://localhost:8003`
- ranking on `http://localhost:8004`
- postgres on `localhost:5432`

### Start the backend-only stack

```bash
docker compose -f services/docker-compose.yml up --build
```

On startup, the compose stack now runs `db/init_db.sql` and all files in `db/migrations/` through a dedicated migration step before the coordinator starts.

### Apply database migrations

```bash
sh db/migrate.sh infra/docker-compose.yml
```

Or for the backend-only compose file:

```bash
sh db/migrate.sh services/docker-compose.yml
```

This is mainly useful when you want to re-apply the schema manually against an already-running database.

### Helpful Make targets

```bash
make compose-build-all
make up
make down
make migrate-db
make migrate-db-services
```

## Testing

There are unit tests for the coordinator, resume intake, screening, ranking, and audit services under `services/*/tests`.

## Current Gaps

- Ranking can overwrite candidate recommendation and status after the main workflow completes, but ranking artifacts are not persisted in Postgres.
- The frontend includes a `deleteCandidate` API helper, but there is no matching coordinator delete endpoint yet.
- There is no async queue or background worker orchestration yet; batch uploads and workflow execution still run synchronously.
- Heuristic extraction and explanation quality still have room to improve.
