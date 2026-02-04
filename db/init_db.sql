-- ===============================
-- EXTENSIONS
-- ===============================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===============================
-- RESUMES (Ground Truth)
-- ===============================
CREATE TABLE IF NOT EXISTS resumes (
    resume_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_text TEXT NOT NULL,
    structured_data JSONB,
    ingestion_status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_ingestion_status ON resumes (ingestion_status);

-- ===============================
-- AGENT OUTPUTS (Immutable Logs)
-- ===============================
CREATE TABLE IF NOT EXISTS agent_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id UUID NOT NULL,
    agent_name TEXT NOT NULL,
    output JSONB NOT NULL,
    reasoning TEXT,
    confidence FLOAT CHECK (
        confidence BETWEEN 0
        AND 1
    ),
    status TEXT NOT NULL DEFAULT 'SUCCESS',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_agent_resume FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_outputs_resume ON agent_outputs (resume_id);

CREATE INDEX IF NOT EXISTS idx_agent_outputs_agent ON agent_outputs (agent_name);

-- ===============================
-- WORKFLOW STATE (Coordinator Brain)
-- ===============================
CREATE TABLE IF NOT EXISTS workflow_state (
    resume_id UUID PRIMARY KEY,
    current_step TEXT NOT NULL,
    next_step TEXT,
    last_error TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_workflow_resume FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE CASCADE
);

-- ===============================
-- AUDIT VIEW (READ-ONLY)
-- ===============================
CREATE
OR REPLACE VIEW audit_trail AS
SELECT
    r.resume_id,
    r.created_at AS resume_created_at,
    ao.agent_name,
    ao.status,
    ao.confidence,
    ao.reasoning,
    ao.created_at AS agent_timestamp
FROM
    resumes r
    JOIN agent_outputs ao ON r.resume_id = ao.resume_id
ORDER BY
    ao.created_at ASC;