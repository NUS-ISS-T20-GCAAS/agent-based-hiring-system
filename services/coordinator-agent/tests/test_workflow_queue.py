import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.schemas import JobRequest
from app.tasks import run_workflow_task


class WorkflowQueueWorkerTests(unittest.TestCase):
    @patch("app.tasks.emit_agent_activity")
    @patch("app.tasks.run_job")
    def test_run_workflow_task_returns_completed_payload(self, run_job_mock, emit_agent_activity_mock):
        request_payload = JobRequest(
            job_id="job-1",
            resume_url="upload://resume.txt",
            resume_text="Python engineer",
            job_description="Need python",
            required_skills=["python"],
        ).model_dump()

        run_job_mock.return_value = SimpleNamespace(job_id="job-1", artifact_id="artifact-1")

        result = run_workflow_task.run(request_payload, "resume.txt")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["job_id"], "job-1")
        self.assertEqual(result["artifact_id"], "artifact-1")
        self.assertEqual(run_job_mock.call_count, 1)
        self.assertEqual(emit_agent_activity_mock.call_count, 2)

    @patch("app.tasks.emit_agent_activity")
    @patch("app.tasks.run_job", side_effect=HTTPException(status_code=400, detail="bad request"))
    def test_run_workflow_task_returns_failed_payload_for_http_exception(self, _run_job_mock, emit_agent_activity_mock):
        request_payload = JobRequest(
            job_id="job-1",
            resume_url="upload://resume.txt",
            resume_text="Python engineer",
            job_description="Need python",
            required_skills=["python"],
        ).model_dump()

        result = run_workflow_task.run(request_payload, "resume.txt")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["job_id"], "job-1")
        self.assertEqual(result["error"], "bad request")
        self.assertEqual(emit_agent_activity_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
