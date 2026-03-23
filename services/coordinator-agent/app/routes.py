import re
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
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


def _extract_resume_text(raw: bytes) -> str:
    if not raw:
        return ""

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = raw.decode("latin-1", errors="ignore")

    normalized = re.sub(r"\s+", " ", decoded).strip()
    return normalized[:20000]


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
            resume_text = _extract_resume_text(content)
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
    avg_score = _to_float(stats.get("avg_score"))
    pass_rate = 0.0 if total == 0 else shortlisted / total

    return {
        "total_candidates": total,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "avg_score": avg_score,
        "pass_rate": pass_rate,
    }


@router.get("/agents/status")
def get_agent_status():
    checks = [
        ("coordinator", "http://localhost:8000/health"),
        ("resume-intake", f"{RESUME_INTAKE_AGENT_URL}/health"),
        ("screening", f"{SCREENING_AGENT_URL}/health"),
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
    total = int(stats.get("total_candidates") or 0)
    shortlisted = int(stats.get("shortlisted") or 0)
    selection_rate = 0.0 if total == 0 else shortlisted / total

    return {
        "job_id": job_id,
        "selection_rate": selection_rate,
        "total_candidates": total,
        "shortlisted": shortlisted,
        "bias_flags": [],
        "status": "not_implemented",
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
