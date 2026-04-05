"""Celery task definitions for background workflow execution.

Tasks defined here are dispatched by the coordinator API routes (via .delay())
and executed by the Celery worker running in a separate container.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.celery_app import celery
from app.coordinator import run_job
from app.events import emit_agent_activity
from app.logger import get_logger
from app.repository import CoordinatorRepository
from app.schemas import JobRequest

logger = get_logger("celery_tasks")


@celery.task(
    bind=True,
    name="coordinator.run_workflow",
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def run_workflow_task(self, request_payload: dict, filename: str = "resume.txt"):
    """Execute a full candidate workflow as a background Celery task.

    This wraps the existing ``run_job`` function and adds Celery-level
    retry handling on top of the per-agent retries already in the
    coordinator orchestration logic.
    """
    job_id = request_payload.get("job_id", "unknown")
    try:
        request = JobRequest.model_validate(request_payload)

        emit_agent_activity(
            agent="coordinator",
            message=f"Celery worker picked up workflow for {filename}",
            entity_id=request.job_id,
        )

        result = run_job(request)

        emit_agent_activity(
            agent="coordinator",
            message=f"Celery worker completed workflow for {filename}",
            entity_id=request.job_id,
        )

        return {
            "status": "completed",
            "job_id": result.job_id,
            "artifact_id": result.artifact_id,
        }

    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        logger.error(
            "celery_task_http_error",
            filename=filename,
            job_id=job_id,
            status_code=exc.status_code,
            error=detail,
        )
        emit_agent_activity(
            agent="coordinator",
            message=f"Celery task failed for {filename}: {detail}",
            entity_id=job_id,
        )
        if exc.status_code == 503:
            raise self.retry(exc=exc)
        return {"status": "failed", "job_id": job_id, "error": detail}

    except Exception as exc:
        logger.error(
            "celery_task_failed",
            filename=filename,
            job_id=job_id,
            error=str(exc),
        )
        emit_agent_activity(
            agent="coordinator",
            message=f"Celery task failed for {filename}: {exc}",
            entity_id=job_id,
        )
        raise self.retry(exc=exc)
