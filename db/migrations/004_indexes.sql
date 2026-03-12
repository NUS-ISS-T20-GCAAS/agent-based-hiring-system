CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates (job_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_job_id ON artifacts (job_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_candidate_id ON artifacts (candidate_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_type_created ON artifacts (artifact_type, created_at);

CREATE INDEX IF NOT EXISTS idx_workflow_corr ON workflow_runs (correlation_id);
