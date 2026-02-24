import unittest
from unittest.mock import patch

import requests
from fastapi import HTTPException

from app.routes import get_job_artifacts


class FakeResponse:
    def __init__(self, payload: list[dict], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> list[dict]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class RoutesArtifactTests(unittest.TestCase):
    @patch("app.routes.requests.get")
    def test_get_job_artifacts_combines_and_sorts(self, get_mock):
        intake_artifact = {
            "artifact_id": "a-intake",
            "entity_id": "job-1",
            "correlation_id": "cid-1",
            "agent_id": "agent-intake",
            "agent_type": "resume_intake",
            "artifact_type": "resume_intake_result",
            "payload": {"skills": ["python"]},
            "confidence": 0.8,
            "explanation": "intake done",
            "created_at": "2026-02-24T12:00:02+00:00",
            "version": 1,
        }
        screening_artifact = {
            "artifact_id": "a-screen",
            "entity_id": "job-1",
            "correlation_id": "cid-1",
            "agent_id": "agent-screen",
            "agent_type": "screening",
            "artifact_type": "qualification_screening_result",
            "payload": {"qualification_score": 0.71},
            "confidence": 0.9,
            "explanation": "screening done",
            "created_at": "2026-02-24T12:00:03+00:00",
            "version": 1,
        }
        get_mock.side_effect = [
            FakeResponse([intake_artifact]),
            FakeResponse([screening_artifact]),
        ]

        result = get_job_artifacts("job-1")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["artifact_id"], "a-intake")
        self.assertEqual(result[1]["artifact_id"], "a-screen")
        self.assertEqual(get_mock.call_count, 2)

    @patch("app.routes.requests.get")
    def test_get_job_artifacts_returns_503_if_service_down(self, get_mock):
        get_mock.side_effect = requests.exceptions.RequestException("network down")

        with self.assertRaises(HTTPException) as ctx:
            get_job_artifacts("job-2")

        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
