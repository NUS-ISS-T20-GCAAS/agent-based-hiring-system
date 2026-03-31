ALTER TABLE candidates
ADD COLUMN IF NOT EXISTS rank_position INT,
ADD COLUMN IF NOT EXISTS ranking_score NUMERIC(5,4),
ADD COLUMN IF NOT EXISTS ranking_method TEXT,
ADD COLUMN IF NOT EXISTS ranked_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_candidates_job_rank_position
ON candidates (job_id, rank_position);

CREATE INDEX IF NOT EXISTS idx_candidates_job_ranked_at
ON candidates (job_id, ranked_at DESC);
