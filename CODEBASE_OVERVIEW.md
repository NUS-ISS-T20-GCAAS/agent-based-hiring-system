# Agent-Based Hiring System: Codebase & Architecture Overview

This document provides a comprehensive overview of the Agent-Based Hiring System codebase. It is specifically designed to be ingested by tools like NotebookLM and Gemini to generate presentation slides and architectural summaries.

---

## 1. High-Level System Overview

The Agent-Based Hiring System is an explainable, scalable hiring workflow built as a system of cooperating microservices. It leverages multiple specialized AI agents to automate the screening and evaluation of job candidates based on their resumes, providing explainable decisions and natural-language gap analyses.

### Key Capabilities
- Automated parsing of unstructured resumes (PDF, DOCX, TXT).
- Execution of multi-stage AI reasoning loops using specialized agents.
- Storage of workflow artifacts and explainability trails for auditing.
- Human-in-the-loop (HITL) manual overrides via a dedicated Dashboard.
- Cost-optimized AWS-backed cloud infrastructure.

---

## 2. Technology Stack

- **Backend / API Server:** Python 3.11 with FastAPI
- **Frontend / Dashboard:** React 18, Vite, Tailwind CSS (running on Nginx)
- **Database:** PostgreSQL 15 (AWS RDS) for job, candidate, and artifact states
- **Asynchronous Task Queue:** Celery with Redis 7 as the message broker
- **Containerization:** Docker & Docker Compose
- **Infrastructure as Code (IaC):** Terraform
- **Cloud Provider:** AWS (EKS, Fargate, ALB, ECR, RDS, VPC)
- **AI/LLM Integration:** OpenAI API (defaulting to model `gpt-4o-mini`)
- **CI/CD:** GitHub Actions

---

## 3. Core Components & Microservices

The application is broken down into separate microservices under the `services/` directory, managed centrally by the coordinator.

### 3.1 Frontend (`/frontend`)
- **Purpose:** A recruiter-facing dashboard.
- **Features:** View active jobs, candidate details, decision trails, agent health statuses, and aggregated system stats.
- **Real-time:** Uses WebSockets (`/ws`) to receive live UI updates when resumes are uploaded and processed.

### 3.2 Coordinator Agent (`/services/coordinator-agent`)
- **Purpose:** Central orchestration and persistence layer.
- **Responsibilities:** 
  - Exposing REST APIs to the frontend and receiving uploads.
  - Parsing multi-format resumes.
  - Upserting database records via Postgres.
  - Dispatching and coordinating the step-by-step workflow across the other specialized AI agents.

### 3.3 Resume Intake Agent (`/services/resume-intake-agent`)
- **Purpose:** Data extraction and normalization.
- **Responsibilities:** Converts raw resume text into a structured JSON candidate profile (Name, Email, Skills, Experience).

### 3.4 Skill Assessment Agent (`/services/skill-assessment-agent`)
- **Purpose:** Competency profiling.
- **Responsibilities:** Evaluates the candidate's skills against job requirements to produce a "Gap Analysis" report, identifying missing and matched competencies.

### 3.5 Screening Agent (`/services/screening-agent`)
- **Purpose:** Qualification and Threshold Evaluation.
- **Responsibilities:** Calculates qualification scores, emits recommendation signals (Shortlist/Reject), and raises human review flags if the candidate is an edge case.

### 3.6 Audit Agent (`/services/audit-agent`)
- **Purpose:** Bias, consistency, and compliance checks (Explainable AI - XRAI).
- **Responsibilities:** Compiles timestamped decision records from previous agents and evaluates them for potential bias, assigning a risk-level and determining if manual human review is necessary.

### 3.7 Ranking Agent (`/services/ranking-agent`)
- **Purpose:** Candidate sorting and recommendation.
- **Responsibilities:** This is a manually triggered service (`POST /jobs/{job_id}/rank`) that ranks candidates within a given job post using enriched data and decision trail artifacts.

---

## 4. Primary Workflows

### 4.1 Job Creation & Candidate Upload Workflow
1. **Initiation:** Recruiter hits `POST /jobs/create` to set up job metadata.
2. **Upload:** Recruiter uploads resumes via `POST /candidates/upload` or `POST /candidates/batch-upload`. 
3. **Queueing:** The Coordinator handles file extraction and submits a task payload into Redis, returning a `202 Accepted` to the client.

### 4.2 Asynchronous Agent Evaluation Workflow
1. A background **Celery Worker** (running the coordinator logic) picks up the task from Redis.
2. Initial DB state is committed (job row, candidate row, workflow execution row).
3. **Step 1:** Sends resume text to the **Resume Intake Agent** to obtain structured parameters.
4. **Step 2:** Forwards structured profile and job requirements to the **Skill Assessment Agent**.
5. **Step 3:** Forwards updated context to the **Screening Agent** to determine shortlisting.
6. **Step 4:** Packages up all decisions and forwards to the **Audit Agent** for bias/compliance verification.
7. **Completion:** The Coordinator combines composite scores, calculates the final `status`, stores all `artifacts` in PostgreSQL, and marks the run as complete. 

---

## 5. Persistence & Data Model

All states are handled securely by **PostgreSQL 15**:
- `jobs`: Stores structural requirements, position description, required vs. preferred skills.
- `candidates`: Represents parsed personal information, assigned score, rank, and review status (e.g. `needs_human_review`).
- `workflow_runs`: A tracking table maintaining the `correlation_id` across distinct background jobs.
- `artifacts`: Persisted JSON-like blobs containing the step-by-step logic, confidence scores, and explanations made by each AI sub-agent.

---

## 6. Cloud Infrastructure & CI/CD (AWS & Terraform)

All cloud infrastructure is declared in `infra/terraform/`. The deployment automates high-availability, scalability, and secure networking.

### Infrastructure Highlights:
- **Compute:** AWS Elastic Kubernetes Service (EKS) utilizing Fargate for serverless and auto-scaling container execution.
- **Networking:** Custom VPC, NAT Gateway, Application Load Balancer (ALB) attached to a public domain (`sentinelrecruit.me`).
- **Data:** AWS RDS for Postgres 15 ensuring daily backups and scaling.
- **Registry:** Elastic Container Registry (ECR) hosting Docker images for every decoupled microservice.

### CI/CD Pipelines (GitHub Actions):
- Located in `.github/workflows/`.
- Automated build, test, and ECR container publishing for: `frontend`, `coordinator-agent`, `resume-intake-agent`, `screening-agent`, `skill-assessment-agent`, `audit-agent`, `ranking-agent`.
- Automatic Terraform apply on infrastructure changes.

### Cost-Saving Mechanism
An innovative, on-demand infrastructure scaling approach is implemented via the **"Terraform Manage (Destroy / Recreate) for cost saving"** GitHub Workflow. 
- During off-hours, it automatically tears down the expensive EKS control plane and NAT Gateway (saving ~$105/month).
- It explicitly preserves the Database (RDS) and Container Registry (ECR), allowing rapid environment resurrection without data loss.

---

## 7. Future Horizons / Ongoing Work
- Maturing LangGraph integrations for strict state checks.
- Expanding MLSecOps pipelines (Trivy image scanning, Promptfoo evaluations, DeepEval checks for hallunications/toxicity).
- Fine-tuning the LLM prompts and incorporating stronger heuristics processing as an offline fallback strategy.
