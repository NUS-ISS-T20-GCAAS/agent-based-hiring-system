# CI/CD Workflows (`.github/workflows`)

This directory contains the GitHub Actions workflows that dictate the Continuous Integration, Continuous Deployment, and Cost-Optimization mechanics for the Agent-Based Hiring System. 

The strategy isolates build logic into reusable workflows, promotes artifacts through immutable registries (GHCR to AWS ECR), and seamlessly integrates Terraform Infrastructure-as-code deployments directly alongside Kubernetes workloads.

## Pipeline Overview

### 1. Application Deployment Pipelines

These pipelines are responsible for taking application code, building images, and launching them into the AWS Kubernetes (EKS) cluster.

*   **`deploy-services.yml` (Backend Microservices)**
    *   **Trigger:** Push to `services/**` or manually dispatched.
    *   **Process:** 
        1. Calls the reusable `build.yml` pipeline dynamically, building images for all relevant sub-projects (`coordinator-agent`, `skill-assessment-agent`, etc.).
        2. Transfers only successful builds from GitHub Container Registry (GHCR) to Amazon Elastic Container Registry (ECR).
        3. Authenticates with EKS, substitutes environment placeholders (like `<IMAGE_TAG>` and `<ACCOUNT_ID>`) in `infra/terraform/k8s/`, and applies the exact manifests using `kubectl`.

*   **`deploy-frontend.yml` (React Frontend)**
    *   **Trigger:** Push to `frontend/**` or manually dispatched.
    *   **Process:** Similar architecture to the backend. Calls the reusable `frontend-build.yml` pipeline (which performs multi-stage Vite builds), promotes securely to ECR, and updates the EKS `frontend` namespace with zero-downtime rollouts.

*   **`deploy-db.yml` (Database Migrations)**
    *   **Trigger:** Push to `db/**`.
    *   **Process:** Executes safely within the GitHub runner by pulling the current live AWS RDS hostname implicitly via `terraform output`. Installs raw PostgreSQL clients and executes `db/init_db.sql` and `db/migrations/*.sql` incrementally. 

### 2. Infrastructure & Cost Optimization Pipelines 

These pipelines operate using Terraform to shape the EKS clusters, NAT gateways, and VPC layout backing the application layer.

*   **`terraform.yml` (Primary Infrastructure Deploy)**
    *   **Trigger:** Push to `infra/terraform/**` or manually dispatched.
    *   **Process:** Ensures AWS cloud state matches code. Connects securely using OIDC/IAM credentials to run `terraform fmt`, `validate`, `plan`, and `apply`. Acts as the master orchestrator, injecting AWS resource ARNs directly into foundational Kubernetes configuration layers (e.g. installing AWS Load Balancer Controllers into EKS).

*   **`terraform-manage.yml` (Cost Optimization)**
    *   **Trigger:** Manually dispatched.
    *   **Process:** Handles non-production development environments. 
        *   **Suspend:** Triggers a targeted granular `terraform destroy` shutting down expensive hourly configurations (such as EKS nodes, NAT Gateways, Elastic IPs). Critical persistent data configurations (ECR Images, RDS databases) remain untouched. Before destroying, the step extracts all current live running Kubernetes Image tags and zips them as artifacts.
        *   **Restore:** Blocked securely by a GitHub Environment manual approval. When approved, re-runs Terraforms `apply`, re-installs Load Balancer controllers, and uses a python script to unpack the saved tags artifact, restoring the exact pod workload versions that existed prior to suspension. 

### 3. Reusable Workflows & Testing

*   **`build.yml` / `frontend-build.yml`**
    *   Modular scripts explicitly designed to just execute `docker build` & `docker push` up to GHCR. 
*   **`llm-eval.yml` (Prompt and Quality Evaluation)**
    *   **Trigger:** Code changes inside the intelligent service implementations (e.g., `app/llm.py`).
    *   **Process:** Runs `DeepEval` and `Promptfoo` frameworks evaluating precision and hallucinations across LLM modifications recursively against OpenAI API test beds before merging. 

---

## Required Repositiory Secrets
These pipelines expect the following secrets configured at your GitHub Repository Settings layer:
*   `AWS_ACCESS_KEY_ID`: For secure programmatic terraform deployments
*   `AWS_SECRET_ACCESS_KEY`: For secure programmatic terraform deployments
*   `TF_VAR_DB_PASSWORD`: Password initialized for the primary RDS database instance
*   `OPENAI_API_KEY`: Fed directly into k8s secure Secret stores for LLM agent runtime and `llm-eval.yml` validation logic.
