CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    correlation_id UUID NOT NULL,
    current_step TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    retry_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id UUID PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    correlation_id UUID NOT NULL,
    agent_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    confidence NUMERIC(4,3) NOT NULL CHECK (
        confidence BETWEEN 0
        AND 1
    ),
    explanation TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL
);
