from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor

from app.db import transaction
from app.schemas import Artifact, JobRequest


class CoordinatorRepository:
    @staticmethod
    def _ranking_outcome(score: float) -> tuple[str, str]:
        if score >= 0.70:
            return "SHORTLIST", "shortlisted"
        if score >= 0.45:
            return "CONSIDER", "screened"
        return "REJECT", "rejected"

    def upsert_job(
        self,
        *,
        job_id: str,
        job_description: str,
        job_requirements: dict[str, Any],
        title: str | None = None,
    ) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO jobs (job_id, title, job_description, job_requirements, status)
                    VALUES (%s, %s, %s, %s::jsonb, 'PROCESSING')
                    ON CONFLICT (job_id)
                    DO UPDATE
                    SET
                        title = EXCLUDED.title,
                        job_description = EXCLUDED.job_description,
                        job_requirements = EXCLUDED.job_requirements,
                        updated_at = NOW()
                    """,
                    (job_id, title or job_id, job_description, Json(job_requirements or {})),
                )

    def create_candidate(
        self,
        *,
        job_id: str,
        resume_url: str,
        resume_text: str | None,
        correlation_id: str,
    ) -> str:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO candidates (
                        job_id,
                        resume_url,
                        resume_text,
                        status,
                        recommendation,
                        correlation_id
                    )
                    VALUES (%s, %s, %s, 'processing', 'PENDING', %s::uuid)
                    RETURNING candidate_id
                    """,
                    (job_id, resume_url, resume_text, correlation_id),
                )
                candidate_id = cur.fetchone()[0]
                return str(candidate_id)

    def start_workflow_run(
        self,
        *,
        job_id: str,
        candidate_id: str,
        correlation_id: str,
        current_step: str,
    ) -> str:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_runs (
                        job_id,
                        candidate_id,
                        correlation_id,
                        current_step,
                        status
                    )
                    VALUES (%s, %s::uuid, %s::uuid, %s, 'RUNNING')
                    RETURNING run_id
                    """,
                    (job_id, candidate_id, correlation_id, current_step),
                )
                run_id = cur.fetchone()[0]
                return str(run_id)

    def update_workflow_step(self, *, run_id: str, current_step: str) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET current_step = %s
                    WHERE run_id = %s::uuid
                    """,
                    (current_step, run_id),
                )

    def save_artifact(
        self,
        *,
        job_id: str,
        candidate_id: str,
        artifact: Artifact,
    ) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO artifacts (
                        artifact_id,
                        job_id,
                        candidate_id,
                        correlation_id,
                        agent_id,
                        agent_type,
                        artifact_type,
                        payload,
                        confidence,
                        explanation,
                        version,
                        created_at
                    )
                    VALUES (
                        %s::uuid,
                        %s,
                        %s::uuid,
                        %s::uuid,
                        %s,
                        %s,
                        %s,
                        %s::jsonb,
                        %s,
                        %s,
                        %s,
                        %s::timestamptz
                    )
                    """,
                    (
                        artifact.artifact_id,
                        job_id,
                        candidate_id,
                        artifact.correlation_id,
                        artifact.agent_id,
                        artifact.agent_type,
                        artifact.artifact_type,
                        Json(artifact.payload if artifact.payload is not None else {}),
                        artifact.confidence,
                        artifact.explanation,
                        artifact.version,
                        artifact.created_at,
                    ),
                )

    def enqueue_workflow_job(
        self,
        *,
        job_id: str,
        filename: str,
        request: JobRequest,
    ) -> str:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_queue (
                        job_id,
                        filename,
                        request_payload,
                        status
                    )
                    VALUES (%s, %s, %s::jsonb, 'PENDING')
                    RETURNING queue_id::text
                    """,
                    (job_id, filename, Json(request.model_dump())),
                )
                queue_id = cur.fetchone()[0]
                return str(queue_id)

    def claim_next_workflow_job(self) -> dict[str, Any] | None:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    WITH next_job AS (
                        SELECT queue_id
                        FROM workflow_queue
                        WHERE status = 'PENDING'
                        ORDER BY created_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE workflow_queue AS q
                    SET
                        status = 'RUNNING',
                        attempt_count = q.attempt_count + 1,
                        started_at = NOW(),
                        last_error = NULL
                    FROM next_job
                    WHERE q.queue_id = next_job.queue_id
                    RETURNING
                        q.queue_id::text AS queue_id,
                        q.job_id,
                        q.filename,
                        q.request_payload,
                        q.attempt_count,
                        q.created_at,
                        q.started_at
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def mark_workflow_job_completed(self, *, queue_id: str) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_queue
                    SET
                        status = 'COMPLETED',
                        finished_at = NOW()
                    WHERE queue_id = %s::uuid
                    """,
                    (queue_id,),
                )

    def mark_workflow_job_failed(self, *, queue_id: str, error: str) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_queue
                    SET
                        status = 'FAILED',
                        last_error = %s,
                        finished_at = NOW()
                    WHERE queue_id = %s::uuid
                    """,
                    (error, queue_id),
                )

    def get_workflow_queue_counts(self) -> dict[str, int]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'PENDING')::int AS pending,
                        COUNT(*) FILTER (WHERE status = 'RUNNING')::int AS running,
                        COUNT(*) FILTER (WHERE status = 'FAILED')::int AS failed,
                        COUNT(*) FILTER (WHERE status = 'COMPLETED')::int AS completed
                    FROM workflow_queue
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else {
                    "pending": 0,
                    "running": 0,
                    "failed": 0,
                    "completed": 0,
                }

    def mark_workflow_failed(
        self,
        *,
        job_id: str,
        run_id: str,
        candidate_id: str,
        step: str,
        error: str,
    ) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET
                        status = 'FAILED',
                        current_step = %s,
                        last_error = %s,
                        finished_at = NOW()
                    WHERE run_id = %s::uuid
                    """,
                    (step, error, run_id),
                )
                cur.execute(
                    """
                    UPDATE candidates
                    SET
                        status = 'rejected',
                        recommendation = 'REJECT',
                        updated_at = NOW()
                    WHERE candidate_id = %s::uuid
                    """,
                    (candidate_id,),
                )
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'FAILED', updated_at = NOW()
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )

    def complete_workflow(
        self,
        *,
        job_id: str,
        candidate_id: str,
        run_id: str,
        intake_payload: dict[str, Any] | None,
        skill_payload: dict[str, Any] | None,
        screening_payload: dict[str, Any] | None,
        review_state: dict[str, Any] | None,
    ) -> None:
        intake_payload = intake_payload or {}
        skill_payload = skill_payload or {}
        screening_payload = screening_payload or {}
        review_state = review_state or {}

        try:
            skills_score = float(skill_payload.get("skills_score"))
            skills_score = max(0.0, min(1.0, skills_score))
        except (TypeError, ValueError):
            matched = screening_payload.get("matched_skills") or []
            missing = screening_payload.get("missing_skills") or []
            skills_denominator = len(matched) + len(missing)
            skills_score = 0.0 if skills_denominator == 0 else len(matched) / skills_denominator

        qualification_score = float(screening_payload.get("qualification_score") or 0.0)
        composite_score = round((qualification_score * 0.7) + (skills_score * 0.3), 4)
        meets_threshold = bool(screening_payload.get("meets_threshold"))

        recommendation = "SHORTLIST" if meets_threshold else "REJECT"
        status = "shortlisted" if meets_threshold else "rejected"

        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE candidates
                    SET
                        name = COALESCE(%s, name),
                        email = COALESCE(%s, email),
                        skills = %s::jsonb,
                        status = %s,
                        recommendation = %s,
                        qualification_score = %s,
                        skills_score = %s,
                        composite_score = %s,
                        needs_human_review = %s,
                        review_status = %s,
                        review_reasons = %s::jsonb,
                        escalation_source = %s,
                        updated_at = NOW()
                    WHERE candidate_id = %s::uuid
                    """,
                    (
                        intake_payload.get("name"),
                        intake_payload.get("email"),
                        Json(intake_payload.get("skills") or []),
                        status,
                        recommendation,
                        qualification_score,
                        round(skills_score, 4),
                        composite_score,
                        bool(review_state.get("needs_human_review")),
                        review_state.get("review_status") or "not_required",
                        Json(review_state.get("review_reasons") or []),
                        review_state.get("escalation_source") or "none",
                        candidate_id,
                    ),
                )

                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET
                        status = 'COMPLETED',
                        current_step = 'done',
                        finished_at = NOW()
                    WHERE run_id = %s::uuid
                    """,
                    (run_id,),
                )

                cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'COMPLETED', updated_at = NOW()
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )

    def list_jobs(self) -> list[dict[str, Any]]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        j.job_id,
                        j.title,
                        j.job_description,
                        j.job_requirements,
                        j.status,
                        j.created_at,
                        j.updated_at,
                        COUNT(c.candidate_id)::int AS candidates_count
                    FROM jobs j
                    LEFT JOIN candidates c ON c.job_id = j.job_id
                    GROUP BY j.job_id, j.title, j.job_description, j.job_requirements, j.status, j.created_at, j.updated_at
                    ORDER BY j.created_at DESC
                    """
                )
                return list(cur.fetchall())

    def get_job(self, *, job_id: str) -> dict[str, Any] | None:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        j.job_id,
                        j.title,
                        j.job_description,
                        j.job_requirements,
                        j.status,
                        j.created_at,
                        j.updated_at,
                        COUNT(c.candidate_id)::int AS candidates_count
                    FROM jobs j
                    LEFT JOIN candidates c ON c.job_id = j.job_id
                    WHERE j.job_id = %s
                    GROUP BY j.job_id, j.title, j.job_description, j.job_requirements, j.status, j.created_at, j.updated_at
                    """,
                    (job_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def list_candidates(self, *, job_id: str | None = None) -> list[dict[str, Any]]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        candidate_id::text AS id,
                        job_id,
                        name,
                        email,
                        phone,
                        skills,
                        status,
                        recommendation,
                        qualification_score,
                        skills_score,
                        composite_score,
                        rank_position,
                        ranking_score,
                        ranking_method,
                        ranked_at,
                        needs_human_review,
                        review_status,
                        review_reasons,
                        escalation_source,
                        created_at,
                        updated_at
                    FROM candidates
                    WHERE (%s::text IS NULL OR job_id = %s)
                    ORDER BY
                        CASE
                            WHEN %s::text IS NULL THEN 0
                            WHEN rank_position IS NULL THEN 1
                            ELSE 0
                        END,
                        CASE WHEN %s::text IS NULL THEN NULL ELSE rank_position END ASC NULLS LAST,
                        composite_score DESC NULLS LAST,
                        created_at DESC
                    """,
                    (job_id, job_id, job_id, job_id),
                )
                return list(cur.fetchall())

    def get_candidate(self, *, candidate_id: str) -> dict[str, Any] | None:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        candidate_id::text AS id,
                        job_id,
                        name,
                        email,
                        phone,
                        skills,
                        status,
                        recommendation,
                        qualification_score,
                        skills_score,
                        composite_score,
                        rank_position,
                        ranking_score,
                        ranking_method,
                        ranked_at,
                        needs_human_review,
                        review_status,
                        review_reasons,
                        escalation_source,
                        created_at,
                        updated_at
                    FROM candidates
                    WHERE candidate_id = %s::uuid
                    """,
                    (candidate_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def delete_candidate(self, *, candidate_id: str) -> bool:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM candidates
                    WHERE candidate_id = %s::uuid
                    """,
                    (candidate_id,),
                )
                return cur.rowcount > 0

    def get_candidate_decisions(self, *, candidate_id: str) -> list[dict[str, Any]]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        artifact_id::text AS decision_id,
                        agent_id,
                        artifact_type,
                        explanation,
                        confidence,
                        created_at
                    FROM artifacts
                    WHERE candidate_id = %s::uuid
                    ORDER BY created_at ASC
                    """,
                    (candidate_id,),
                )
                return list(cur.fetchall())

    def list_artifacts(self, *, job_id: str | None = None) -> list[dict[str, Any]]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        artifact_id::text AS artifact_id,
                        job_id AS entity_id,
                        candidate_id::text AS candidate_id,
                        correlation_id::text AS correlation_id,
                        agent_id,
                        agent_type,
                        artifact_type,
                        payload,
                        confidence,
                        explanation,
                        version,
                        created_at
                    FROM artifacts
                    WHERE (%s::text IS NULL OR job_id = %s)
                    ORDER BY created_at ASC
                    """,
                    (job_id, job_id),
                )
                return list(cur.fetchall())

    def get_stats(self, *, job_id: str | None = None) -> dict[str, Any]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)::int AS total_candidates,
                        COUNT(*) FILTER (WHERE status = 'shortlisted')::int AS shortlisted,
                        COUNT(*) FILTER (WHERE status = 'rejected')::int AS rejected,
                        COUNT(*) FILTER (WHERE needs_human_review = TRUE)::int AS review_required,
                        COALESCE(AVG(composite_score), 0) AS avg_score
                    FROM candidates
                    WHERE (%s::text IS NULL OR job_id = %s)
                    """,
                    (job_id, job_id),
                )
                row = cur.fetchone()
                return dict(row) if row else {
                    "total_candidates": 0,
                    "shortlisted": 0,
                    "rejected": 0,
                    "review_required": 0,
                    "avg_score": 0,
                }

    def apply_candidate_ranking(
        self,
        *,
        job_id: str,
        ranked_candidates: list[dict[str, Any]],
        ranking_method: str | None = None,
        ranked_at: str | None = None,
    ) -> int:
        updates: list[tuple[int, float, str | None, str | None, str, str]] = []
        for index, item in enumerate(ranked_candidates, start=1):
            candidate_id = item.get("candidate_id") or item.get("id")
            if not isinstance(candidate_id, str) or not candidate_id.strip():
                continue

            score_value = item.get("score")
            score = float(score_value) if isinstance(score_value, (int, float)) else 0.0
            method = item.get("method") if isinstance(item.get("method"), str) else ranking_method
            updates.append((index, round(score, 4), method, ranked_at, candidate_id, job_id))

        if not updates:
            return 0

        with transaction() as conn:
            with conn.cursor() as cur:
                updated = 0
                for rank_position, score, method, rank_timestamp, candidate_id, entity_job_id in updates:
                    cur.execute(
                        """
                        UPDATE candidates
                        SET
                            rank_position = %s,
                            ranking_score = %s,
                            ranking_method = %s,
                            ranked_at = COALESCE(%s::timestamptz, NOW()),
                            updated_at = NOW()
                        WHERE candidate_id = %s::uuid
                          AND job_id = %s
                        """,
                        (rank_position, score, method, rank_timestamp, candidate_id, entity_job_id),
                    )
                    updated += cur.rowcount

                if updated > 0:
                    cur.execute(
                        """
                        UPDATE jobs
                        SET status = 'COMPLETED', updated_at = NOW()
                        WHERE job_id = %s
                        """,
                        (job_id,),
                    )
                return updated
