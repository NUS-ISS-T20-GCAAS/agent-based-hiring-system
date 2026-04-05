-- Migration 009: Drop tables replaced by Celery + Redis
--
-- workflow_queue: Previously used for Postgres-backed job
-- dispatch. Now replaced by Celery tasks dispatched through Redis.
--
-- workflow_state: Legacy table from the original init_db.sql schema.
-- Never referenced by the coordinator application code. Superseded
-- by the workflow_runs table (which is kept).

DROP TABLE IF EXISTS workflow_queue;

DROP TABLE IF EXISTS workflow_state;
