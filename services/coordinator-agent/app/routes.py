import re
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
import requests

from app.schemas import JobRequest, JobResponse, Artifact
from app.coordinator import run_job
from app.repository import CoordinatorRepository
from app.resume_parser import ResumeParsingError, extract_resume_text

from app.config import AUDIT_AGENT_URL, RESUME_INTAKE_AGENT_URL, SCREENING_AGENT_URL, REQUEST_TIMEOUT
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


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


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


def _normalize_job_requirements(value: object) -> dict:
    if not isinstance(value, dict):
        return {}

    required_skills = value.get("required_skills")
    preferred_skills = value.get("preferred_skills")

    return {
        "required_skills": required_skills if isinstance(required_skills, list) else [],
        "preferred_skills": preferred_skills if isinstance(preferred_skills, list) else [],
        "min_years_experience": value.get("min_years_experience"),
        "education_level": value.get("education_level"),
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _job_payload(row: dict) -> dict:
    job_requirements = _normalize_job_requirements(row.get("job_requirements"))
    required_skills = job_requirements["required_skills"] or _extract_required_skills(row.get("job_description"))
    return {
        "job_id": row["job_id"],
        "title": row.get("title") or row["job_id"],
        "job_description": row.get("job_description") or "",
        "status": (row.get("status") or "").lower(),
        "required_skills": required_skills,
        "preferred_skills": job_requirements["preferred_skills"],
        "min_years_experience": job_requirements["min_years_experience"],
        "education_level": job_requirements["education_level"],
        "candidates_count": int(row.get("candidates_count") or 0),
    }


def _candidate_payload(row: dict) -> dict:
    skills = row.get("skills") if isinstance(row.get("skills"), list) else []
    review_reasons = _string_list(row.get("review_reasons"))
    needs_human_review = bool(row.get("needs_human_review"))
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
        "needs_human_review": needs_human_review,
        "review_status": row.get("review_status") or ("pending" if needs_human_review else "not_required"),
        "review_reasons": review_reasons,
        "escalation_source": row.get("escalation_source") or "none",
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


def _artifact_payload(row: dict) -> dict:
    created_at = row.get("created_at")
    timestamp = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    return {
        "artifact_id": row.get("artifact_id"),
        "entity_id": row.get("entity_id"),
        "candidate_id": row.get("candidate_id"),
        "correlation_id": row.get("correlation_id"),
        "agent_id": row.get("agent_id"),
        "agent_type": row.get("agent_type"),
        "artifact_type": row.get("artifact_type"),
        "payload": row.get("payload"),
        "confidence": _to_float(row.get("confidence")),
        "explanation": row.get("explanation"),
        "created_at": timestamp,
        "version": int(row.get("version") or 1),
    }


def _job_or_404(repository: CoordinatorRepository, job_id: str) -> dict:
    row = repository.get_job(job_id=job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row


@router.post("/jobs", response_model=JobResponse)
def submit_job(request: JobRequest):
    return run_job(request)


@router.get("/jobs")
def list_jobs():
    repository = CoordinatorRepository()
    rows = repository.list_jobs()
    return [_job_payload(row) for row in rows]


@router.post("/jobs/{job_id}/rank")
def rank_job_candidates(job_id: str):
    repository = CoordinatorRepository()
    _job_or_404(repository, job_id)
    ranked = repository.rank_candidates(job_id=job_id)
    return {
        "job_id": job_id,
        "ranked_candidates": ranked,
        "status": "completed",
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    repository = CoordinatorRepository()
    row = _job_or_404(repository, job_id)
    return _job_payload(row)


@router.get("/candidates")
def list_candidates(job_id: str | None = Query(default=None)):
    repository = CoordinatorRepository()
    rows = repository.list_candidates(job_id=job_id)
    return [_candidate_payload(row) for row in rows]


async def _process_upload_files(
    *,
    repository: CoordinatorRepository,
    job_id: str,
    files: list[UploadFile],
) -> dict:
    job = _job_or_404(repository, job_id)
    job_description = job.get("job_description") or ""
    job_requirements = _normalize_job_requirements(job.get("job_requirements"))

    results: list[dict] = []
    errors: list[dict] = []

    for upload in files:
        filename = upload.filename or "resume.txt"
        try:
            content = await upload.read()
            resume_text = extract_resume_text(
                filename=filename,
                content_type=getattr(upload, "content_type", None),
                raw=content,
            )
            request = JobRequest(
                job_id=job_id,
                resume_url=f"upload://{filename}",
                resume_text=resume_text,
                job_description=job_description,
                required_skills=job_requirements["required_skills"],
                preferred_skills=job_requirements["preferred_skills"],
                min_years_experience=job_requirements["min_years_experience"],
                education_level=job_requirements["education_level"],
            )
            job_response = run_job(request)
            results.append(job_response.model_dump())
        except ResumeParsingError as exc:
            errors.append(
                {
                    "file": filename,
                    "detail": exc.detail,
                    "status_code": exc.status_code,
                }
            )
        except HTTPException as exc:
            errors.append(
                {
                    "file": filename,
                    "detail": exc.detail,
                    "status_code": exc.status_code,
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "file": filename,
                    "detail": str(exc),
                    "status_code": 500,
                }
            )
        finally:
            await upload.close()

    return {
        "job_id": job_id,
        "processed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.post("/candidates/upload")
async def upload_candidate(job_id: str = Query(...), file: UploadFile = File(...)):
    repository = CoordinatorRepository()
    result = await _process_upload_files(repository=repository, job_id=job_id, files=[file])

    if result["processed"] == 0:
        first_error = result["errors"][0] if result["errors"] else {"detail": "upload failed", "status_code": 500}
        raise HTTPException(status_code=first_error["status_code"], detail=first_error["detail"])

    return result["results"][0]


@router.post("/candidates/batch-upload")
async def upload_candidates(job_id: str = Query(...), files: list[UploadFile] = File(...)):
    repository = CoordinatorRepository()
    result = await _process_upload_files(repository=repository, job_id=job_id, files=files)

    if result["processed"] == 0:
        first_error = result["errors"][0] if result["errors"] else {"detail": "batch upload failed", "status_code": 500}
        raise HTTPException(status_code=first_error["status_code"], detail=first_error["detail"])

    return result


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
    review_required = int(stats.get("review_required") or 0)
    avg_score = _to_float(stats.get("avg_score"))
    pass_rate = 0.0 if total == 0 else shortlisted / total

    return {
        "total_candidates": total,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "review_required": review_required,
        "avg_score": avg_score,
        "pass_rate": pass_rate,
    }


@router.get("/agents/status")
def get_agent_status():
    checks = [
        ("coordinator", "http://localhost:8000/health"),
        ("resume-intake", f"{RESUME_INTAKE_AGENT_URL}/health"),
        ("screening", f"{SCREENING_AGENT_URL}/health"),
        ("audit", f"{AUDIT_AGENT_URL}/health"),
    ]

    services = []
    for name, url in checks:
        try:
            resp = requests.get(url, timeout=2)
            services.append(
                {
                    "agent": name,
                    "status": "online" if resp.ok else "degraded",
                    "http_status": resp.status_code,
                }
            )
        except Exception as exc:
            services.append({"agent": name, "status": "offline", "error": str(exc)})

    overall = "online" if all(x["status"] == "online" for x in services) else "degraded"
    return {"status": overall, "services": services}


@router.get("/audit/bias-check")
def get_bias_check(job_id: str | None = Query(default=None)):
    repository = CoordinatorRepository()
    stats = repository.get_stats(job_id=job_id)
    candidates = repository.list_candidates(job_id=job_id)
    decisions = repository.list_artifacts(job_id=job_id)

    try:
        resp = requests.post(
            f"{AUDIT_AGENT_URL}/run",
            json=_json_safe({
                "entity_id": job_id or "global-audit",
                "correlation_id": f"audit-read-{job_id or 'all'}",
                "input_data": {
                    "job_id": job_id,
                    "stats": stats,
                    "candidates": candidates,
                    "decisions": decisions,
                },
            }),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        artifact = Artifact.model_validate(resp.json())
        if isinstance(artifact.payload, dict):
            return {
                **artifact.payload,
                "artifact_id": artifact.artifact_id,
                "agent_id": artifact.agent_id,
                "agent_type": artifact.agent_type,
                "artifact_type": artifact.artifact_type,
                "confidence": artifact.confidence,
                "explanation": artifact.explanation,
                "created_at": artifact.created_at,
                "version": artifact.version,
                "correlation_id": artifact.correlation_id,
            }
        return artifact.model_dump()
    except requests.exceptions.RequestException as exc:
        logger.error(
            "audit_fetch_failed",
            entity_id=job_id or "all",
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail="audit unavailable")


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: str):
    repository = CoordinatorRepository()
    _job_or_404(repository, job_id)
    rows = repository.list_artifacts(job_id=job_id)
    return [_artifact_payload(row) for row in rows]
