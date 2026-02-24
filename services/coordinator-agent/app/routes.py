from datetime import datetime
from fastapi import APIRouter, HTTPException
import requests

from app.schemas import JobRequest, JobResponse, Artifact
from app.coordinator import run_job

from app.config import RESUME_INTAKE_AGENT_URL, SCREENING_AGENT_URL, REQUEST_TIMEOUT
from app.logger import get_logger

router = APIRouter()
logger = get_logger("routes")

@router.post("/jobs", response_model=JobResponse)
def submit_job(request: JobRequest):
    return run_job(request)


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
