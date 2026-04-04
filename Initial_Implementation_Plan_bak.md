# Implementation Plan: Agent-Based Hiring System for Scalable and Explainable Resume Screening

## Phase 1: Cloud & Local Infrastructure Setup (Estimated: 40 man-hours)
**Objective:** Provision the cloud infrastructure and establish a reproducible local development environment.
*   **Cloud Provisioning (Terraform):** Write Infrastructure-as-Code (IaC) using Terraform to provision AWS EKS (Elastic Kubernetes Service) for hosting the microservices and agents, and AWS RDS (PostgreSQL) for scalable, centralized long-term state and audit logging. 
*   **Local Development (Docker Compose):** Create a `docker-compose.yml` file to spin up local instances of PostgreSQL, FastAPI, and MLflow for local testing before cloud deployment [1, 2].
*   **Backend Initialization:** Set up a FastAPI application using Python 3.11 to serve as the primary API Gateway, handling frontend requests and routing them to the multi-agent system [1, 3].

## Phase 2: Multi-Agent Orchestration & State Management (Estimated: 80 man-hours)
**Objective:** Establish the communication topology and shared memory architecture for the agents.
*   **Agent Topology (LangGraph):** Implement a Supervisor or Custom workflow architecture using LangGraph [4, 5]. The Coordinator Agent will act as the central supervisor, dynamically managing task delegation, priority queueing, and conflict resolution across the sub-agents [4].
*   **Shared Memory & State Payload:** Define a strongly typed `State` dictionary in Python to act as the "Shared Memory Layer" [6]. This state will persist the resume data, extracted skills, and intermediate agent reasoning loops.
*   **Long-Term Memory:** Connect the LangGraph state checkpointer to your PostgreSQL database to maintain conversation history and cross-session context [7]. 

## Phase 3: Specialized Agent Development (Estimated: 150 man-hours)
**Objective:** Develop the core functional agents utilizing the OpenAI API and agentic reasoning patterns.
*   **Resume Intake Agent:** Build an agent to extract and normalize text from PDFs/Word documents, converting unstructured data into a structured JSON payload stored in PostgreSQL.
*   **Qualification Screening Agent:** Implement ReAct (Reason + Act) prompting to evaluate candidate credentials against hard filters (e.g., location, legal constraints) and preferred qualifications [8, 9].
*   **Skill Assessment Agent:** Use the OpenAI API (e.g., GPT-4o) to perform semantic mapping and generate a "Gap Analysis" report identifying matched and missing competencies [10, 11]. 
*   **Ranking & Recommendation Agent:** Aggregate the scores from the shared state to calculate a final ranking, generating natural-language shortlists based on decision thresholds.
*   **Tool Integration via MCP:** Construct a Tool Gateway using the Model Context Protocol (MCP) to securely standardize how these agents discover and invoke external tools, such as LinkedIn APIs, Applicant Tracking Systems (ATS), and calendar scheduling [12, 13].

## Phase 4: Explainable AI (XRAI) & Cybersecurity Defenses (Estimated: 100 man-hours)
**Objective:** Implement safeguards, auditability, and human-centric escalation paths.
*   **Explanation & Audit Agent:** Design this agent to compile timestamped decision records from all other agents. Utilize techniques inspired by the Contrastive Explanation Method (CEM) to highlight features that, if changed, would alter the prediction, providing clear "Why" and "How to be that" justifications for the Ranking Agent's decisions [14, 15].
*   **Human-in-the-Loop (HITL) Protocol:** Configure the Audit Agent to suspend autonomous execution and flag decisions to a human recruiter via FastAPI endpoints if confidence scores fall below a threshold or if conflicting agent results are detected [16, 17].
*   **AI Cybersecurity Controls:** Apply Input/Output Filtering to sanitize incoming resumes against Prompt Injections [18, 19]. Use Spotlighting techniques to clearly separate candidate data from system instructions, ensuring the model does not obey hidden commands [20, 21].

## Phase 5: MLSecOps Pipeline & Automated Testing (Estimated: 120 man-hours)
**Objective:** Automate the testing, tracking, and deployment of the system to AWS EKS.
*   **LLM Evaluation:** Write automated test scripts using DeepEval to assess hallucination rates, bias, toxicity, and answer relevancy during the screening process [22-24]. Use Promptfoo to catch regressions in prompt performance when tuning parameters [25, 26].
*   **Experiment Tracking:** Integrate MLflow to log prompt versions, OpenAI model versions, and hyperparameter configurations (like temperature settings) [2, 27].
*   **Container Security:** Add Trivy to your pipeline to scan Docker images and dependencies for vulnerabilities before deployment [28, 29].
*   **CI/CD with GitHub Actions:** Create workflows that automatically run DeepEval/Promptfoo tests, build the Docker images, push them to a container registry, and deploy them to the AWS EKS cluster [30, 31].

## Phase 6: Observability & Demonstration Readiness (Estimated: 60 man-hours)
**Objective:** Ensure system health monitoring and prepare the XRAI dashboard for presentation.
*   **Agent Tracing:** Integrate Langfuse to trace the multi-agent execution paths, token usage, latency, and evaluate outputs directly within the application [31, 32]. 
*   **System Monitoring:** Utilize EKS-compatible tools like Prometheus and Grafana to track aggregate system health, tokens per request, FastAPI request success rates, and PostgreSQL connection loads [33, 34].
*   **Explainability Dashboard (Frontend):** Build a simple frontend interface to visualize the agent chain-of-thought, the gap analysis reports, and the HITL escalation queue for the final project demonstration.


# Details to be confirmed
*   Database design
*   Agent design
*   Frontend design
*   Verify if all application works in AWS with DB

https://nc.me/github/auth?domain=sentinelrecruit.me