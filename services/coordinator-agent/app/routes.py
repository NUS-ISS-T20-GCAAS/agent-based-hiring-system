from fastapi import APIRouter, HTTPException
import requests

from app.schemas import JobRequest, JobResponse
from app.coordinator import run_job

from app.config import RESUME_INTAKE_AGENT_URL, REQUEST_TIMEOUT
from app.logger import get_logger

router = APIRouter()
logger = get_logger("routes")

@router.post("/jobs", response_model=JobResponse)
def submit_job(request: JobRequest):
    return run_job(request)


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: str):
    try:
        resp = requests.get(
            f"{RESUME_INTAKE_AGENT_URL}/artifacts/{job_id}",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        validated = [Artifact.model_validate(x).model_dump() for x in data]
        return validated

    except requests.exceptions.RequestException as e:
        logger.error("artifacts_fetch_failed", entity_id=job_id, error=str(e))
        raise HTTPException(status_code=503, detail="resume-intake unavailable")

    except Exception as e:
        logger.error("artifacts_proxy_crashed", entity_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"proxy failed: {type(e).__name__}")
