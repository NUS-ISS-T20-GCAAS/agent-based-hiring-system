import unittest
import asyncio
import io
from typing import Optional
from unittest.mock import patch

import requests
from fastapi import HTTPException
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.routes import (
    get_job_artifacts,
    list_jobs,
    get_job,
    list_candidates,
    get_candidate,
    get_candidate_decisions,
    get_stats,
    rank_job_candidates,
    upload_candidate,
    upload_candidates,
)


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class FakeRepository:
    def list_jobs(self):
        return [
            {
                "job_id": "job-1",
                "title": "Backend Engineer",
                "job_description": "Need python fastapi and sql",
                "job_requirements": {
                    "required_skills": ["python", "fastapi", "sql"],
                    "preferred_skills": ["docker"],
                    "min_years_experience": 3,
                    "education_level": "Bachelor's",
                },
                "status": "COMPLETED",
                "candidates_count": 2,
            }
        ]

    def get_job(self, *, job_id: str):
        if job_id == "missing":
            return None
        return {
            "job_id": job_id,
            "title": "Backend Engineer",
            "job_description": "Need python fastapi",
            "job_requirements": {
                "required_skills": ["python", "fastapi"],
                "preferred_skills": ["docker"],
                "min_years_experience": 3,
                "education_level": "Bachelor's",
            },
            "status": "COMPLETED",
            "candidates_count": 1,
        }

    def list_candidates(self, *, job_id=None):
        return [
            {
                "id": "c-1",
                "job_id": job_id or "job-1",
                "name": "Alice",
                "email": "alice@example.com",
                "phone": None,
                "skills": ["python", "fastapi"],
                "status": "shortlisted",
                "recommendation": "SHORTLIST",
                "qualification_score": 0.8,
                "skills_score": 0.7,
                "composite_score": 0.77,
                "needs_human_review": True,
                "review_status": "pending",
                "review_reasons": ["Screening: confidence 65% below floor 70%"],
                "escalation_source": "screening",
            }
        ]

    def get_candidate(self, *, candidate_id: str):
        if candidate_id == "missing":
            return None
        return {
            "id": candidate_id,
            "job_id": "job-1",
            "name": "Alice",
            "email": "alice@example.com",
            "phone": None,
            "skills": ["python", "fastapi"],
            "status": "shortlisted",
            "recommendation": "SHORTLIST",
            "qualification_score": 0.8,
            "skills_score": 0.7,
            "composite_score": 0.77,
            "needs_human_review": True,
            "review_status": "pending",
            "review_reasons": ["Screening: confidence 65% below floor 70%"],
            "escalation_source": "screening",
        }

    def get_candidate_decisions(self, *, candidate_id: str):
        return [
            {
                "decision_id": "d-1",
                "agent_id": "screening-agent",
                "artifact_type": "qualification_screening_result",
                "explanation": "score high",
                "confidence": 0.9,
                "created_at": "2026-03-12T12:00:00+00:00",
            }
        ]

    def list_artifacts(self, *, job_id=None):
        return [
            {
                "artifact_id": "a-intake",
                "entity_id": job_id or "job-1",
                "candidate_id": "c-1",
                "correlation_id": "cid-1",
                "agent_id": "resume-intake-agent",
                "agent_type": "resume_intake",
                "artifact_type": "resume_intake_result",
                "payload": {"skills": ["python"]},
                "confidence": 0.8,
                "explanation": "intake done",
                "created_at": "2026-02-24T12:00:02+00:00",
                "version": 1,
            },
            {
                "artifact_id": "a-audit",
                "entity_id": job_id or "job-1",
                "candidate_id": "c-1",
                "correlation_id": "cid-1",
                "agent_id": "audit-agent",
                "agent_type": "audit",
                "artifact_type": "audit_bias_check_result",
                "payload": {"risk_level": "low", "review_required": False},
                "confidence": 0.88,
                "explanation": "audit done",
                "created_at": "2026-02-24T12:00:04+00:00",
                "version": 1,
            },
        ]

    def get_stats(self, *, job_id=None):
        return {
            "total_candidates": 10,
            "shortlisted": 4,
            "rejected": 6,
            "review_required": 2,
            "avg_score": 0.66,
        }

    def rank_candidates(self, *, job_id: str):
        return 1


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes, content_type: Optional[str] = None):
        self.filename = filename
        self._content = content
        self.content_type = content_type

    async def read(self):
        return self._content

    async def close(self):
        return None


def build_pdf_bytes(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=144)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): font_ref,
                }
            )
        }
    )

    content_stream = DecodedStreamObject()
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream.set_data(f"BT /F1 18 Tf 36 100 Td ({escaped_text}) Tj ET".encode("utf-8"))
    page[NameObject("/Contents")] = writer._add_object(content_stream)

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class RoutesReadApiTests(unittest.TestCase):
    @patch("app.routes.CoordinatorRepository")
    def test_jobs_candidates_and_stats_routes(self, repo_cls):
        repo_cls.return_value = FakeRepository()

        jobs = list_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["job_id"], "job-1")
        self.assertEqual(jobs[0]["required_skills"], ["python", "fastapi", "sql"])
        self.assertEqual(jobs[0]["preferred_skills"], ["docker"])
        self.assertEqual(jobs[0]["min_years_experience"], 3)

        job = get_job("job-1")
        self.assertEqual(job["title"], "Backend Engineer")
        self.assertEqual(job["required_skills"], ["python", "fastapi"])

        candidates = list_candidates(job_id="job-1")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["id"], "c-1")
        self.assertEqual(candidates[0]["scores"]["composite"], 0.77)
        self.assertTrue(candidates[0]["needs_human_review"])
        self.assertEqual(candidates[0]["review_status"], "pending")

        candidate = get_candidate("c-1")
        self.assertEqual(candidate["name"], "Alice")
        self.assertEqual(candidate["escalation_source"], "screening")
        self.assertEqual(candidate["review_reasons"], ["Screening: confidence 65% below floor 70%"])

        decisions = get_candidate_decisions("c-1")
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision_type"], "qualification_screening_result")

        artifacts = get_job_artifacts("job-1")
        self.assertEqual(len(artifacts), 2)
        self.assertEqual(artifacts[1]["artifact_type"], "audit_bias_check_result")

        stats = get_stats(job_id="job-1")
        self.assertEqual(stats["total_candidates"], 10)
        self.assertEqual(stats["shortlisted"], 4)
        self.assertEqual(stats["review_required"], 2)
        self.assertAlmostEqual(stats["pass_rate"], 0.4)

        rank_result = rank_job_candidates("job-1")
        self.assertEqual(rank_result["ranked_candidates"], 1)

    @patch("app.routes.CoordinatorRepository")
    def test_not_found_routes(self, repo_cls):
        repo_cls.return_value = FakeRepository()

        with self.assertRaises(HTTPException) as job_ctx:
            get_job("missing")
        self.assertEqual(job_ctx.exception.status_code, 404)

        with self.assertRaises(HTTPException) as candidate_ctx:
            get_candidate("missing")
        self.assertEqual(candidate_ctx.exception.status_code, 404)

    @patch("app.routes.requests.post")
    @patch("app.routes.CoordinatorRepository")
    def test_bias_check_route_uses_audit_agent(self, repo_cls, post_mock):
        repo_cls.return_value = FakeRepository()
        post_mock.return_value = FakeResponse(
            {
                "artifact_id": "a-audit-live",
                "entity_id": "job-1",
                "correlation_id": "cid-live",
                "agent_id": "audit-agent",
                "agent_type": "audit",
                "artifact_type": "audit_bias_check_result",
                "payload": {
                    "job_id": "job-1",
                    "selection_rate": 0.4,
                    "total_candidates": 10,
                    "shortlisted": 4,
                    "bias_flags": [],
                    "risk_level": "low",
                    "review_required": False,
                    "recommendations": ["continue monitoring"],
                },
                "confidence": 0.9,
                "explanation": "audit complete",
                "created_at": "2026-03-25T10:00:00+00:00",
                "version": 1,
            }
        )

        from app.routes import get_bias_check

        result = get_bias_check(job_id="job-1")

        self.assertEqual(result["job_id"], "job-1")
        self.assertEqual(result["artifact_type"], "audit_bias_check_result")
        self.assertAlmostEqual(result["selection_rate"], 0.4)
        self.assertFalse(result["review_required"])
        self.assertEqual(post_mock.call_count, 1)

    @patch("app.routes.run_job")
    @patch("app.routes.CoordinatorRepository")
    def test_batch_upload_route(self, repo_cls, run_job_mock):
        repo_cls.return_value = FakeRepository()
        run_job_mock.return_value = type(
            "JobResponseObj",
            (),
            {"model_dump": lambda self: {"job_id": "job-1", "status": "completed", "artifact_id": "a-1"}},
        )()

        files = [
            FakeUploadFile("a.txt", b"Python FastAPI engineer", "text/plain"),
            FakeUploadFile("b.txt", b"SQL and AWS", "text/plain"),
        ]

        result = asyncio.run(upload_candidates(job_id="job-1", files=files))
        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["failed"], 0)
        first_request = run_job_mock.call_args_list[0].args[0]
        self.assertEqual(first_request.required_skills, ["python", "fastapi"])
        self.assertEqual(first_request.preferred_skills, ["docker"])
        self.assertEqual(first_request.min_years_experience, 3)

    @patch("app.routes.run_job")
    @patch("app.routes.CoordinatorRepository")
    def test_batch_upload_route_extracts_txt_pdf_and_docx(self, repo_cls, run_job_mock):
        repo_cls.return_value = FakeRepository()
        run_job_mock.return_value = type(
            "JobResponseObj",
            (),
            {"model_dump": lambda self: {"job_id": "job-1", "status": "completed", "artifact_id": "a-1"}},
        )()

        files = [
            FakeUploadFile("resume.txt", b"Senior Python engineer", "text/plain"),
            FakeUploadFile("resume.pdf", build_pdf_bytes("PDF Resume Text"), "application/pdf"),
            FakeUploadFile(
                "resume.docx",
                build_docx_bytes("DOCX Resume Text"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ]

        result = asyncio.run(upload_candidates(job_id="job-1", files=files))

        self.assertEqual(result["processed"], 3)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(len(run_job_mock.call_args_list), 3)
        self.assertEqual(run_job_mock.call_args_list[0].args[0].resume_text, "Senior Python engineer")
        self.assertIn("PDF Resume Text", run_job_mock.call_args_list[1].args[0].resume_text)
        self.assertIn("DOCX Resume Text", run_job_mock.call_args_list[2].args[0].resume_text)

    @patch("app.routes.run_job")
    @patch("app.routes.CoordinatorRepository")
    def test_upload_route_rejects_unsupported_resume_type(self, repo_cls, run_job_mock):
        repo_cls.return_value = FakeRepository()

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                upload_candidate(
                    job_id="job-1",
                    file=FakeUploadFile("resume.png", b"binary", "image/png"),
                )
            )

        self.assertEqual(ctx.exception.status_code, 415)
        self.assertIn("unsupported resume file type", ctx.exception.detail)
        self.assertEqual(run_job_mock.call_count, 0)

    @patch("app.routes.run_job")
    @patch("app.routes.CoordinatorRepository")
    def test_batch_upload_reports_empty_and_corrupt_documents(self, repo_cls, run_job_mock):
        repo_cls.return_value = FakeRepository()

        files = [
            FakeUploadFile("empty.txt", b"", "text/plain"),
            FakeUploadFile("broken.pdf", b"%PDF-1.4 broken", "application/pdf"),
        ]

        result = asyncio.run(upload_candidates(job_id="job-1", files=files))

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["errors"][0]["file"], "empty.txt")
        self.assertIn("empty", result["errors"][0]["detail"].lower())
        self.assertEqual(result["errors"][1]["file"], "broken.pdf")
        self.assertIn("failed to extract text from pdf resume", result["errors"][1]["detail"].lower())
        self.assertEqual(run_job_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
