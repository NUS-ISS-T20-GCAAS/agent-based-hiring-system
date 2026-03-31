from __future__ import annotations

import threading
from typing import Callable

from fastapi import HTTPException

from app.coordinator import run_job
from app.logger import get_logger
from app.repository import CoordinatorRepository
from app.schemas import JobRequest
from app.config import QUEUE_POLL_INTERVAL_SECONDS
from app.events import emit_agent_activity

logger = get_logger("workflow_queue")


class WorkflowQueueWorker:
    def __init__(
        self,
        *,
        repository_factory: Callable[[], CoordinatorRepository] = CoordinatorRepository,
        run_job_fn: Callable[[JobRequest], object] = run_job,
        poll_interval_seconds: float = QUEUE_POLL_INTERVAL_SECONDS,
    ) -> None:
        self._repository_factory = repository_factory
        self._run_job = run_job_fn
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def poll_interval_seconds(self) -> float:
        return self._poll_interval_seconds

    def start(self) -> None:
        if self.is_running():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="workflow-queue-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("workflow_queue_worker_started", poll_interval_seconds=self._poll_interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(self._poll_interval_seconds * 2, 1.0))
        logger.info("workflow_queue_worker_stopped")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def process_next_job(self) -> bool:
        repository = self._repository_factory()
        queued_job = repository.claim_next_workflow_job()
        if not queued_job:
            return False

        queue_id = queued_job["queue_id"]
        filename = queued_job.get("filename") or "resume.txt"

        try:
            request = JobRequest.model_validate(queued_job.get("request_payload") or {})
            emit_agent_activity(
                agent="coordinator",
                message=f"Dequeued upload workflow for {filename}",
                entity_id=request.job_id,
            )
            self._run_job(request)
            repository.mark_workflow_job_completed(queue_id=queue_id)
            emit_agent_activity(
                agent="coordinator",
                message=f"Completed queued upload workflow for {filename}",
                entity_id=request.job_id,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            repository.mark_workflow_job_failed(queue_id=queue_id, error=detail)
            logger.error(
                "workflow_queue_job_failed",
                queue_id=queue_id,
                filename=filename,
                error=detail,
            )
            job_id = queued_job.get("job_id")
            if isinstance(job_id, str):
                emit_agent_activity(
                    agent="coordinator",
                    message=f"Queued upload failed for {filename}: {detail}",
                    entity_id=job_id,
                )
        except Exception as exc:
            repository.mark_workflow_job_failed(queue_id=queue_id, error=str(exc))
            logger.error(
                "workflow_queue_job_failed",
                queue_id=queue_id,
                filename=filename,
                error=str(exc),
            )
            job_id = queued_job.get("job_id")
            if isinstance(job_id, str):
                emit_agent_activity(
                    agent="coordinator",
                    message=f"Queued upload failed for {filename}: {exc}",
                    entity_id=job_id,
                )

        return True

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = self.process_next_job()
            except Exception as exc:
                logger.error("workflow_queue_poll_failed", error=str(exc))
                processed = False
            if processed:
                continue
            self._stop_event.wait(self._poll_interval_seconds)


workflow_queue_worker = WorkflowQueueWorker()
