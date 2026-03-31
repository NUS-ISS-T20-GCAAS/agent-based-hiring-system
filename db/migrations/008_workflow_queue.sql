CREATE TABLE IF NOT EXISTS workflow_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    request_payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workflow_queue_status_created_at
ON workflow_queue (status, created_at);

CREATE INDEX IF NOT EXISTS idx_workflow_queue_job_created_at
ON workflow_queue (job_id, created_at DESC);
