import unittest
from fastapi import HTTPException

from app.schemas import JobRequest
from app.workflow_queue import WorkflowQueueWorker


class FakeQueueRepository:
    def __init__(self, queued_job=None):
        self.queued_job = queued_job
        self.completed_queue_id = None
        self.failed = None

    def claim_next_workflow_job(self):
        job = self.queued_job
        self.queued_job = None
        return job

    def mark_workflow_job_completed(self, *, queue_id: str):
        self.completed_queue_id = queue_id

    def mark_workflow_job_failed(self, *, queue_id: str, error: str):
        self.failed = {
            "queue_id": queue_id,
            "error": error,
        }


class WorkflowQueueWorkerTests(unittest.TestCase):
    def test_process_next_job_runs_claimed_request_and_marks_complete(self):
        queued_job = {
            "queue_id": "queue-1",
            "job_id": "job-1",
            "filename": "resume.txt",
            "request_payload": JobRequest(
                job_id="job-1",
                resume_url="upload://resume.txt",
                resume_text="Python engineer",
                job_description="Need python",
                required_skills=["python"],
            ).model_dump(),
        }
        repository = FakeQueueRepository(queued_job=queued_job)
        seen_requests = []
        worker = WorkflowQueueWorker(
            repository_factory=lambda: repository,
            run_job_fn=lambda request: seen_requests.append(request),
            poll_interval_seconds=0.01,
        )

        processed = worker.process_next_job()

        self.assertTrue(processed)
        self.assertEqual(repository.completed_queue_id, "queue-1")
        self.assertIsNone(repository.failed)
        self.assertEqual(len(seen_requests), 1)
        self.assertEqual(seen_requests[0].job_id, "job-1")

    def test_process_next_job_marks_failure_when_workflow_raises(self):
        queued_job = {
            "queue_id": "queue-2",
            "job_id": "job-1",
            "filename": "resume.txt",
            "request_payload": JobRequest(
                job_id="job-1",
                resume_url="upload://resume.txt",
                resume_text="Python engineer",
                job_description="Need python",
            ).model_dump(),
        }
        repository = FakeQueueRepository(queued_job=queued_job)

        def failing_run_job(_request):
            raise HTTPException(status_code=503, detail="audit unavailable")

        worker = WorkflowQueueWorker(
            repository_factory=lambda: repository,
            run_job_fn=failing_run_job,
            poll_interval_seconds=0.01,
        )

        processed = worker.process_next_job()

        self.assertTrue(processed)
        self.assertIsNone(repository.completed_queue_id)
        self.assertEqual(
            repository.failed,
            {
                "queue_id": "queue-2",
                "error": "audit unavailable",
            },
        )

    def test_process_next_job_returns_false_when_queue_is_empty(self):
        repository = FakeQueueRepository()
        worker = WorkflowQueueWorker(
            repository_factory=lambda: repository,
            run_job_fn=lambda _request: None,
            poll_interval_seconds=0.01,
        )

        self.assertFalse(worker.process_next_job())


if __name__ == "__main__":
    unittest.main()
