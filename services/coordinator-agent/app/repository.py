from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor

from app.db import transaction
from app.schemas import Artifact


class CoordinatorRepository:
    def upsert_job(self, *, job_id: str, job_description: str) -> None:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO jobs (job_id, title, job_description, status)
                    VALUES (%s, %s, %s, 'PROCESSING')
                    ON CONFLICT (job_id)
                    DO UPDATE
                    SET
                        job_description = EXCLUDED.job_description,
                        updated_at = NOW()
                    """,
                    (job_id, job_id, job_description),
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
        screening_payload: dict[str, Any] | None,
    ) -> None:
        intake_payload = intake_payload or {}
        screening_payload = screening_payload or {}

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
                        j.status,
                        j.created_at,
                        j.updated_at,
                        COUNT(c.candidate_id)::int AS candidates_count
                    FROM jobs j
                    LEFT JOIN candidates c ON c.job_id = j.job_id
                    GROUP BY j.job_id, j.title, j.job_description, j.status, j.created_at, j.updated_at
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
                        j.status,
                        j.created_at,
                        j.updated_at,
                        COUNT(c.candidate_id)::int AS candidates_count
                    FROM jobs j
                    LEFT JOIN candidates c ON c.job_id = j.job_id
                    WHERE j.job_id = %s
                    GROUP BY j.job_id, j.title, j.job_description, j.status, j.created_at, j.updated_at
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
                        created_at,
                        updated_at
                    FROM candidates
                    WHERE (%s::text IS NULL OR job_id = %s)
                    ORDER BY composite_score DESC NULLS LAST, created_at DESC
                    """,
                    (job_id, job_id),
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
                        created_at,
                        updated_at
                    FROM candidates
                    WHERE candidate_id = %s::uuid
                    """,
                    (candidate_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

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

    def get_stats(self, *, job_id: str | None = None) -> dict[str, Any]:
        with transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)::int AS total_candidates,
                        COUNT(*) FILTER (WHERE status = 'shortlisted')::int AS shortlisted,
                        COUNT(*) FILTER (WHERE status = 'rejected')::int AS rejected,
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
                    "avg_score": 0,
                }

    def rank_candidates(self, *, job_id: str) -> int:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE candidates
                    SET
                        skills_score = COALESCE(skills_score, 0),
                        qualification_score = COALESCE(qualification_score, 0),
                        composite_score = ROUND(
                            (
                                COALESCE(qualification_score, 0) * 0.7
                                + COALESCE(skills_score, 0) * 0.3
                            )::numeric,
                            4
                        ),
                        recommendation = CASE
                            WHEN (
                                COALESCE(qualification_score, 0) * 0.7
                                + COALESCE(skills_score, 0) * 0.3
                            ) >= 0.70 THEN 'SHORTLIST'
                            WHEN (
                                COALESCE(qualification_score, 0) * 0.7
                                + COALESCE(skills_score, 0) * 0.3
                            ) >= 0.45 THEN 'CONSIDER'
                            ELSE 'REJECT'
                        END,
                        status = CASE
                            WHEN (
                                COALESCE(qualification_score, 0) * 0.7
                                + COALESCE(skills_score, 0) * 0.3
                            ) >= 0.70 THEN 'shortlisted'
                            WHEN (
                                COALESCE(qualification_score, 0) * 0.7
                                + COALESCE(skills_score, 0) * 0.3
                            ) >= 0.45 THEN 'screened'
                            ELSE 'rejected'
                        END,
                        updated_at = NOW()
                    WHERE job_id = %s
                    """,
                    (job_id,),
                )
                updated = cur.rowcount
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
