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


class FakeRepository:
    def __init__(self):
        self.completed_workflow_kwargs = None

    def upsert_job(self, **_kwargs):
        return None

    def create_candidate(self, **_kwargs):
        return "11111111-1111-1111-1111-111111111111"

    def start_workflow_run(self, **_kwargs):
        return "22222222-2222-2222-2222-222222222222"

    def update_workflow_step(self, **_kwargs):
        return None

    def save_artifact(self, **_kwargs):
        return None

    def list_candidates(self, **_kwargs):
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "skills_score": 0.3,
                "composite_score": 0.4,
                "status": "processing",
                "recommendation": "PENDING",
            }
        ]

    def list_artifacts(self, **_kwargs):
        return []

    def get_stats(self, **_kwargs):
        return {
            "total_candidates": 1,
            "shortlisted": 0,
            "rejected": 0,
            "avg_score": 0.0,
        }

    def mark_workflow_failed(self, **_kwargs):
        return None

    def complete_workflow(self, **_kwargs):
        self.completed_workflow_kwargs = _kwargs
        return None


class CoordinatorRunJobTests(unittest.TestCase):
    @patch("app.coordinator.emit_candidate_update")
    @patch("app.coordinator.emit_agent_activity")
    @patch("app.coordinator.time.sleep", return_value=None)
    @patch("app.coordinator.requests.post")
    def test_run_job_calls_intake_then_skill_assessment_then_screening_then_audit(
        self,
        post_mock,
        _sleep_mock,
        agent_activity_mock,
        candidate_update_mock,
    ):
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
        skill_artifact = {
            "artifact_id": "a-skill",
            "entity_id": "job-123",
            "correlation_id": "cid-1",
            "agent_id": "agent-skill",
            "agent_type": "skill_assessment",
            "artifact_type": "skill_assessment_result",
            "payload": {
                "skills_score": 0.8,
                "matched_required_skills": ["python"],
                "missing_required_skills": ["fastapi"],
                "matched_preferred_skills": [],
                "missing_preferred_skills": ["docker"],
                "detected_soft_skills": ["communication"],
                "strengths": ["python"],
                "gaps": ["fastapi"],
                "gap_analysis": "Skill assessment summary",
            },
            "confidence": 0.84,
            "explanation": "skill assessment ok",
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
            "payload": {
                "qualification_score": 0.75,
                "meets_threshold": True,
                "needs_human_review": True,
                "review_reasons": ["confidence 65% below floor 70%"],
            },
            "confidence": 0.9,
            "explanation": "screening ok",
            "created_at": "2026-02-24T12:00:01+00:00",
            "version": 1,
        }
        audit_artifact = {
            "artifact_id": "a-audit",
            "entity_id": "job-123",
            "correlation_id": "cid-1",
            "agent_id": "agent-audit",
            "agent_type": "audit",
            "artifact_type": "audit_bias_check_result",
            "payload": {
                "job_id": "job-123",
                "selection_rate": 1.0,
                "total_candidates": 1,
                "shortlisted": 1,
                "bias_flags": ["low_selection_rate"],
                "risk_level": "low",
                "review_required": True,
                "recommendations": ["continue monitoring"],
            },
            "confidence": 0.86,
            "explanation": "audit ok",
            "created_at": "2026-02-24T12:00:02+00:00",
            "version": 1,
        }
        post_mock.side_effect = [
            FakeResponse(intake_artifact),
            FakeResponse(skill_artifact),
            FakeResponse(screening_artifact),
            FakeResponse(audit_artifact),
        ]

        req = JobRequest(
            job_id="job-123",
            resume_url="https://example.com/resume.pdf",
            resume_text="Python developer with 5 years",
            job_description="Need python fastapi",
            required_skills=["python", "fastapi"],
            preferred_skills=["docker"],
            min_years_experience=3,
        )

        repository = FakeRepository()
        result = run_job(req, repository=repository)

        self.assertEqual(result.job_id, "job-123")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.artifact_id, "a-audit")
        self.assertEqual(post_mock.call_count, 4)

        first_payload = post_mock.call_args_list[0].kwargs["json"]
        second_payload = post_mock.call_args_list[1].kwargs["json"]
        third_payload = post_mock.call_args_list[2].kwargs["json"]
        fourth_payload = post_mock.call_args_list[3].kwargs["json"]

        self.assertEqual(first_payload["entity_id"], "job-123")
        self.assertEqual(first_payload["input_data"]["resume_url"], "https://example.com/resume.pdf")
        self.assertEqual(first_payload["correlation_id"], second_payload["correlation_id"])
        self.assertEqual(second_payload["correlation_id"], third_payload["correlation_id"])
        self.assertEqual(third_payload["correlation_id"], fourth_payload["correlation_id"])
        self.assertEqual(
            second_payload["input_data"]["parsed_resume"],
            intake_artifact["payload"],
        )
        self.assertEqual(
            second_payload["input_data"]["job_requirements"],
            {
                "required_skills": ["python", "fastapi"],
                "preferred_skills": ["docker"],
                "min_years_experience": 3,
                "education_level": None,
            },
        )
        self.assertEqual(second_payload["input_data"]["resume_text"], "Python developer with 5 years")
        self.assertEqual(
            third_payload["input_data"]["skill_assessment"],
            skill_artifact["payload"],
        )
        self.assertEqual(fourth_payload["input_data"]["job_id"], "job-123")
        self.assertEqual(fourth_payload["input_data"]["stats"]["shortlisted"], 1)
        self.assertEqual(fourth_payload["input_data"]["candidates"][0]["status"], "shortlisted")
        self.assertEqual(fourth_payload["input_data"]["candidates"][0]["scores"]["skills"], 0.8)
        self.assertEqual(repository.completed_workflow_kwargs["skill_payload"], skill_artifact["payload"])
        self.assertEqual(
            repository.completed_workflow_kwargs["review_state"],
            {
                "needs_human_review": True,
                "review_status": "pending",
                "review_reasons": [
                    "Screening: confidence 65% below floor 70%",
                    "Audit: low selection rate",
                ],
                "escalation_source": "screening_and_audit",
            },
        )
        self.assertGreaterEqual(agent_activity_mock.call_count, 6)
        candidate_update_mock.assert_any_call(
            job_id="job-123",
            candidate_id="11111111-1111-1111-1111-111111111111",
            status="processing",
            correlation_id=result.correlation_id,
        )
        candidate_update_mock.assert_any_call(
            job_id="job-123",
            candidate_id="11111111-1111-1111-1111-111111111111",
            status="shortlisted",
            correlation_id=result.correlation_id,
        )

    @patch("app.coordinator.time.sleep", return_value=None)
    @patch("app.coordinator.requests.post")
    def test_run_job_returns_503_when_audit_fails(self, post_mock, _sleep_mock):
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
            FakeResponse(
                {
                    "artifact_id": "a-skill",
                    "entity_id": "job-503",
                    "correlation_id": "cid-2",
                    "agent_id": "agent-skill",
                    "agent_type": "skill_assessment",
                    "artifact_type": "skill_assessment_result",
                    "payload": {"skills_score": 0.65},
                    "confidence": 0.8,
                    "explanation": "skill ok",
                    "created_at": "2026-02-24T12:00:00+00:00",
                    "version": 1,
                }
            ),
            FakeResponse(
                {
                    "artifact_id": "a-screen",
                    "entity_id": "job-503",
                    "correlation_id": "cid-2",
                    "agent_id": "agent-screen",
                    "agent_type": "screening",
                    "artifact_type": "qualification_screening_result",
                    "payload": {"qualification_score": 0.75, "meets_threshold": True},
                    "confidence": 0.9,
                    "explanation": "screening ok",
                    "created_at": "2026-02-24T12:00:01+00:00",
                    "version": 1,
                }
            ),
            requests.exceptions.RequestException("audit down"),
            requests.exceptions.RequestException("audit down"),
            requests.exceptions.RequestException("audit down"),
        ]

        req = JobRequest(
            job_id="job-503",
            resume_url="https://example.com/resume.pdf",
            job_description="Need python",
        )

        with self.assertRaises(HTTPException) as ctx:
            run_job(req, repository=FakeRepository())

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, "audit unavailable")
        self.assertEqual(post_mock.call_count, 6)

    @patch("app.coordinator.time.sleep", return_value=None)
    @patch("app.coordinator.requests.post")
    def test_run_job_sets_audit_only_review_state(self, post_mock, _sleep_mock):
        post_mock.side_effect = [
            FakeResponse(
                {
                    "artifact_id": "a-intake",
                    "entity_id": "job-789",
                    "correlation_id": "cid-3",
                    "agent_id": "agent-intake",
                    "agent_type": "resume_intake",
                    "artifact_type": "resume_intake_result",
                    "payload": {"skills": ["python"], "years_experience": 4},
                    "confidence": 0.8,
                    "explanation": "intake ok",
                    "created_at": "2026-02-24T12:00:00+00:00",
                    "version": 1,
                }
            ),
            FakeResponse(
                {
                    "artifact_id": "a-skill",
                    "entity_id": "job-789",
                    "correlation_id": "cid-3",
                    "agent_id": "agent-skill",
                    "agent_type": "skill_assessment",
                    "artifact_type": "skill_assessment_result",
                    "payload": {
                        "skills_score": 0.7,
                        "matched_required_skills": ["python"],
                        "missing_required_skills": ["fastapi"],
                    },
                    "confidence": 0.82,
                    "explanation": "skill ok",
                    "created_at": "2026-02-24T12:00:00+00:00",
                    "version": 1,
                }
            ),
            FakeResponse(
                {
                    "artifact_id": "a-screen",
                    "entity_id": "job-789",
                    "correlation_id": "cid-3",
                    "agent_id": "agent-screen",
                    "agent_type": "screening",
                    "artifact_type": "qualification_screening_result",
                    "payload": {
                        "qualification_score": 0.91,
                        "meets_threshold": True,
                        "needs_human_review": False,
                        "review_reasons": [],
                    },
                    "confidence": 0.95,
                    "explanation": "screening ok",
                    "created_at": "2026-02-24T12:00:01+00:00",
                    "version": 1,
                }
            ),
            FakeResponse(
                {
                    "artifact_id": "a-audit",
                    "entity_id": "job-789",
                    "correlation_id": "cid-3",
                    "agent_id": "agent-audit",
                    "agent_type": "audit",
                    "artifact_type": "audit_bias_check_result",
                    "payload": {
                        "job_id": "job-789",
                        "selection_rate": 0.25,
                        "total_candidates": 4,
                        "shortlisted": 1,
                        "bias_flags": ["small_sample_size"],
                        "risk_level": "medium",
                        "review_required": True,
                        "recommendations": ["treat as directional"],
                    },
                    "confidence": 0.86,
                    "explanation": "audit ok",
                    "created_at": "2026-02-24T12:00:02+00:00",
                    "version": 1,
                }
            ),
        ]

        repository = FakeRepository()
        run_job(
            JobRequest(
                job_id="job-789",
                resume_url="https://example.com/resume.pdf",
                resume_text="Python developer with 4 years",
                job_description="Need python fastapi",
            ),
            repository=repository,
        )

        self.assertEqual(
            repository.completed_workflow_kwargs["review_state"],
            {
                "needs_human_review": True,
                "review_status": "pending",
                "review_reasons": ["Audit: small sample size"],
                "escalation_source": "audit",
            },
        )


if __name__ == "__main__":
    unittest.main()
