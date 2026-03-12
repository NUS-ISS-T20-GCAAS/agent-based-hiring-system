from __future__ import annotations

from typing import Any

from psycopg2.extras import Json

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
