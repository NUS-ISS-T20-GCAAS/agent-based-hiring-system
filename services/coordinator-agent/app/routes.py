import re
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
import requests

from app.schemas import JobRequest, JobResponse, Artifact
from app.coordinator import run_job
from app.repository import CoordinatorRepository

from app.config import RESUME_INTAKE_AGENT_URL, SCREENING_AGENT_URL, REQUEST_TIMEOUT
from app.logger import get_logger

router = APIRouter()
logger = get_logger("routes")


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _extract_required_skills(job_description: str | None) -> list[str]:
    if not job_description:
        return []

    stop_words = {
        "and",
        "the",
        "with",
        "for",
        "from",
        "that",
        "this",
        "you",
        "your",
        "our",
        "are",
        "will",
        "have",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", job_description.lower())

    seen: set[str] = set()
    skills: list[str] = []
    for word in words:
        if len(word) <= 2 or word in stop_words:
            continue
        if word in seen:
            continue
        seen.add(word)
        skills.append(word)
        if len(skills) >= 8:
            break
    return skills


def _job_payload(row: dict) -> dict:
    return {
        "job_id": row["job_id"],
        "title": row.get("title") or row["job_id"],
        "job_description": row.get("job_description") or "",
        "status": (row.get("status") or "").lower(),
        "required_skills": _extract_required_skills(row.get("job_description")),
        "candidates_count": int(row.get("candidates_count") or 0),
    }


def _candidate_payload(row: dict) -> dict:
    skills = row.get("skills") if isinstance(row.get("skills"), list) else []
    return {
        "id": row["id"],
        "job_id": row.get("job_id"),
        "name": row.get("name") or "Unknown Candidate",
        "email": row.get("email"),
        "phone": row.get("phone"),
        "skills": skills,
        "status": row.get("status") or "processing",
        "recommendation": row.get("recommendation") or "PENDING",
        "scores": {
            "qualification": _to_float(row.get("qualification_score")),
            "skills": _to_float(row.get("skills_score")),
            "composite": _to_float(row.get("composite_score")),
        },
    }


def _decision_payload(row: dict) -> dict:
    created_at = row.get("created_at")
    timestamp = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    return {
        "decision_id": row.get("decision_id"),
        "agent_id": row.get("agent_id"),
        "decision_type": row.get("artifact_type"),
        "reasoning": row.get("explanation"),
        "confidence": _to_float(row.get("confidence")),
        "timestamp": timestamp,
    }


@router.post("/jobs", response_model=JobResponse)
def submit_job(request: JobRequest):
    return run_job(request)


@router.get("/jobs")
def list_jobs():
    repository = CoordinatorRepository()
    rows = repository.list_jobs()
    return [_job_payload(row) for row in rows]


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    repository = CoordinatorRepository()
    row = repository.get_job(job_id=job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return _job_payload(row)


@router.get("/candidates")
def list_candidates(job_id: str | None = Query(default=None)):
    repository = CoordinatorRepository()
    rows = repository.list_candidates(job_id=job_id)
    return [_candidate_payload(row) for row in rows]


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str):
    repository = CoordinatorRepository()
    row = repository.get_candidate(candidate_id=candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="candidate not found")
    return _candidate_payload(row)


@router.get("/candidates/{candidate_id}/decisions")
def get_candidate_decisions(candidate_id: str):
    repository = CoordinatorRepository()
    rows = repository.get_candidate_decisions(candidate_id=candidate_id)
    return [_decision_payload(row) for row in rows]


@router.get("/stats")
def get_stats(job_id: str | None = Query(default=None)):
    repository = CoordinatorRepository()
    stats = repository.get_stats(job_id=job_id)
    total = int(stats.get("total_candidates") or 0)
    shortlisted = int(stats.get("shortlisted") or 0)
    rejected = int(stats.get("rejected") or 0)
    avg_score = _to_float(stats.get("avg_score"))
    pass_rate = 0.0 if total == 0 else shortlisted / total

    return {
        "total_candidates": total,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "avg_score": avg_score,
        "pass_rate": pass_rate,
    }


def _fetch_service_artifacts(job_id: str, *, service_name: str, base_url: str) -> list[Artifact]:
    try:
        resp = requests.get(
            f"{base_url}/artifacts/{job_id}",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return [Artifact.model_validate(x) for x in resp.json()]
    except requests.exceptions.RequestException as exc:
        logger.error(
            "artifacts_fetch_failed",
            entity_id=job_id,
            service=service_name,
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail=f"{service_name} unavailable")


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: str):
    try:
        artifacts = []
        artifacts.extend(
            _fetch_service_artifacts(
                job_id,
                service_name="resume-intake",
                base_url=RESUME_INTAKE_AGENT_URL,
            )
        )
        artifacts.extend(
            _fetch_service_artifacts(
                job_id,
                service_name="screening",
                base_url=SCREENING_AGENT_URL,
            )
        )

        artifacts.sort(key=lambda item: datetime.fromisoformat(item.created_at))
        return [item.model_dump() for item in artifacts]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("artifacts_proxy_crashed", entity_id=job_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"proxy failed: {type(exc).__name__}")
