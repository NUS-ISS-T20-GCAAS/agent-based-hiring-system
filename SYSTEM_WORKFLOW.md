# System Workflow

This document describes the workflow implemented in the current codebase.

## 1. Workflow Summary

The primary synchronous pipeline is:

1. A request reaches the coordinator through `POST /jobs` or a resume upload endpoint.
2. The coordinator upserts the job, creates the candidate, and starts a workflow run.
3. The coordinator sends resume data to the Resume Intake Agent.
4. The Resume Intake Agent returns a structured candidate profile artifact.
5. The coordinator sends the parsed profile plus job context to the Screening Agent.
6. The Screening Agent returns qualification scores, recommendation signals, and review flags.
7. The coordinator builds an audit payload from current stats, candidates, decisions, and the latest screening result.
8. The coordinator sends that payload to the Audit Agent.
9. The Audit Agent returns an audit artifact with risk and review signals.
10. The coordinator persists all artifacts, updates candidate scores and review state, and marks the workflow run as completed.
11. The frontend reads jobs, candidates, stats, decision history, and audit output from the coordinator.

The Ranking Agent is separate from this default flow. It is invoked manually through `POST /jobs/{job_id}/rank`.

## 2. Workflow Diagram

```mermaid
flowchart TD
    A["Recruiter / User"] --> B["Frontend"]
    B --> C["Coordinator API"]
    C --> D["Postgres<br/>jobs, candidates, workflow_runs"]
    C --> E["Resume Intake Agent"]
    E --> F["resume_intake_result artifact"]
    F --> C
    C --> G["Screening Agent"]
    G --> H["qualification_screening_result artifact"]
    H --> C
    C --> I["Audit Agent"]
    I --> J["audit_bias_check_result artifact"]
    J --> C
    C --> K["Postgres<br/>artifacts + candidate state"]
    C --> L["Read APIs"]
    L --> B
    C -. manual .-> M["Ranking Agent"]
    M -. candidate_ranking_result .-> C
```

## 3. Entry Points

### `POST /jobs`

This endpoint is not just job creation. It immediately starts a full workflow run for one candidate input.

Required request fields:

- `job_id`
- `resume_url`
- `job_description`

Optional request fields:

- `resume_text`
- `required_skills`
- `preferred_skills`
- `min_years_experience`
- `education_level`

### `POST /candidates/upload`

Uploads one file for an existing job:

- query param: `job_id`
- multipart field: `file`

### `POST /candidates/batch-upload`

Uploads multiple files for an existing job:

- query param: `job_id`
- multipart field: `files`

Supported upload types:

- `.txt`
- `.pdf`
- `.docx`

## 4. Step-By-Step Flow

### Step 1: Job context is prepared

The coordinator either:

- uses the job data sent to `POST /jobs`, or
- looks up the existing job before processing uploaded resumes.

When listing jobs back to the frontend, the coordinator returns normalized fields such as:

- `title`
- `job_description`
- `required_skills`
- `preferred_skills`
- `min_years_experience`
- `education_level`
- `candidates_count`

If explicit `required_skills` are not stored, the coordinator derives a small skill list from the job description.

### Step 2: Resume text is extracted

For upload endpoints, the coordinator extracts text before calling the agents:

- TXT is decoded directly.
- PDF uses `pypdf`.
- DOCX uses `python-docx`.

Unsupported formats return `415`, and empty or unreadable files return structured parsing errors.

### Step 3: Workflow state is bootstrapped

Before the first agent call, the coordinator:

- upserts the job row
- creates the candidate row
- starts a `workflow_runs` row
- generates a shared `correlation_id`

This makes failures traceable from the first step.

### Step 4: Resume Intake Agent

Input:

- `resume_url`
- `resume_text`
- `job_description`

Output artifact:

- type: `resume_intake_result`
- payload includes normalized candidate fields such as `name`, `email`, `skills`, and `status`

Execution mode:

- OpenAI-backed when configured
- heuristic fallback otherwise

### Step 5: Screening Agent

Input:

- parsed resume payload from intake
- `job_description`
- structured `job_requirements`

Output artifact:

- type: `qualification_screening_result`
- payload includes:
  - `qualification_score`
  - `meets_threshold`
  - `matched_skills`
  - `missing_skills`
  - `decision`
  - `needs_human_review`
  - `review_reasons`

Review flags are raised when the result is borderline, low-confidence, or produced through heuristic fallback.

### Step 6: Audit Agent

The coordinator builds audit input from:

- current job stats
- current candidate list
- persisted decision artifacts
- the latest screening result

Output artifact:

- type: `audit_bias_check_result`
- payload includes:
  - `selection_rate`
  - `bias_flags`
  - `risk_level`
  - `review_required`
  - `recommendations`

### Step 7: Candidate completion and review state

After audit completes, the coordinator:

- persists intake, screening, and audit artifacts
- computes `skills_score`
- computes `composite_score`
- updates candidate `status` and `recommendation`
- combines screening and audit review signals into:
  - `needs_human_review`
  - `review_status`
  - `review_reasons`
  - `escalation_source`
- marks the workflow run as `COMPLETED`
- marks the job as `COMPLETED`

Default coordinator status mapping from screening:

- `meets_threshold = true` -> `SHORTLIST` / `shortlisted`
- `meets_threshold = false` -> `REJECT` / `rejected`

### Step 8: Manual ranking

When `POST /jobs/{job_id}/rank` is called, the coordinator:

- fetches all candidates for the job
- sends them to the Ranking Agent
- applies returned scores back onto candidate rows

The ranking agent is currently heuristic and updates candidate `composite_score`, `recommendation`, and `status`.

## 5. Data Model

The main persisted tables are:

- `jobs`
- `candidates`
- `workflow_runs`
- `artifacts`

Relevant schema additions in the current migration set:

- `jobs.job_requirements`
- `candidates.needs_human_review`
- `candidates.review_status`
- `candidates.review_reasons`
- `candidates.escalation_source`

## 6. Frontend Reality Check

The dashboard is wired to coordinator read APIs for:

- jobs
- candidates
- candidate decision trails
- stats
- agent health
- audit bias checks

The frontend also attempts a WebSocket connection to `/ws`, but there is no WebSocket endpoint in the coordinator service yet. Real-time activity in the UI is therefore not currently backed by the backend.
