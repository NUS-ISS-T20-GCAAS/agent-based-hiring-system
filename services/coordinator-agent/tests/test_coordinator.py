import unittest
from unittest.mock import patch

import requests
from fastapi import HTTPException

from app.coordinator import run_job
from app.schemas import JobRequest


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class CoordinatorRunJobTests(unittest.TestCase):
    @patch("app.coordinator.time.sleep", return_value=None)
    @patch("app.coordinator.requests.post")
    def test_run_job_calls_intake_then_screening(self, post_mock, _sleep_mock):
        intake_artifact = {
            "artifact_id": "a-intake",
            "entity_id": "job-123",
            "correlation_id": "cid-1",
            "agent_id": "agent-intake",
            "agent_type": "resume_intake",
            "artifact_type": "resume_intake_result",
            "payload": {"skills": ["python"], "years_experience": 5},
            "confidence": 0.8,
            "explanation": "intake ok",
            "created_at": "2026-02-24T12:00:00+00:00",
            "version": 1,
        }
        screening_artifact = {
            "artifact_id": "a-screen",
            "entity_id": "job-123",
            "correlation_id": "cid-1",
            "agent_id": "agent-screen",
            "agent_type": "screening",
            "artifact_type": "qualification_screening_result",
            "payload": {"qualification_score": 0.75, "meets_threshold": True},
            "confidence": 0.9,
            "explanation": "screening ok",
            "created_at": "2026-02-24T12:00:01+00:00",
            "version": 1,
        }
        post_mock.side_effect = [FakeResponse(intake_artifact), FakeResponse(screening_artifact)]

        req = JobRequest(
            job_id="job-123",
            resume_url="https://example.com/resume.pdf",
            resume_text="Python developer with 5 years",
            job_description="Need python fastapi",
        )

        result = run_job(req)

        self.assertEqual(result.job_id, "job-123")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.artifact_id, "a-screen")
        self.assertEqual(post_mock.call_count, 2)

        first_payload = post_mock.call_args_list[0].kwargs["json"]
        second_payload = post_mock.call_args_list[1].kwargs["json"]

        self.assertEqual(first_payload["entity_id"], "job-123")
        self.assertEqual(first_payload["input_data"]["resume_url"], "https://example.com/resume.pdf")
        self.assertEqual(first_payload["correlation_id"], second_payload["correlation_id"])
        self.assertEqual(
            second_payload["input_data"]["parsed_resume"],
            intake_artifact["payload"],
        )

    @patch("app.coordinator.time.sleep", return_value=None)
    @patch("app.coordinator.requests.post")
    def test_run_job_returns_503_when_screening_fails(self, post_mock, _sleep_mock):
        intake_artifact = {
            "artifact_id": "a-intake",
            "entity_id": "job-503",
            "correlation_id": "cid-2",
            "agent_id": "agent-intake",
            "agent_type": "resume_intake",
            "artifact_type": "resume_intake_result",
            "payload": {"skills": ["python"], "years_experience": 2},
            "confidence": 0.8,
            "explanation": "intake ok",
            "created_at": "2026-02-24T12:00:00+00:00",
            "version": 1,
        }
        post_mock.side_effect = [
            FakeResponse(intake_artifact),
            requests.exceptions.RequestException("screening down"),
            requests.exceptions.RequestException("screening down"),
            requests.exceptions.RequestException("screening down"),
        ]

        req = JobRequest(
            job_id="job-503",
            resume_url="https://example.com/resume.pdf",
            job_description="Need python",
        )

        with self.assertRaises(HTTPException) as ctx:
            run_job(req)

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, "screening unavailable")
        self.assertEqual(post_mock.call_count, 4)


if __name__ == "__main__":
    unittest.main()
