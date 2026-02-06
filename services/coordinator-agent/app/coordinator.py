import uuid
import time
import requests
from fastapi import HTTPException

from app.schemas import JobRequest, JobResponse, RunRequest, Artifact
from app.logger import get_logger
from app.config import RESUME_INTAKE_AGENT_URL, REQUEST_TIMEOUT

logger = get_logger("coordinator")

MAX_RETRIES = 3
RETRY_DELAY_SEC = 0.5


def run_job(request: JobRequest) -> JobResponse:
    entity_id = request.job_id
    correlation_id = str(uuid.uuid4())

    logger.info("job_received", entity_id=entity_id, correlation_id=correlation_id)

    run_req = RunRequest(
        entity_id=entity_id,
        correlation_id=correlation_id,
        input_data={
            "resume_url": request.resume_url,
            "job_description": request.job_description,
        },
    )

    last_err: Exception | None = None
    resp = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "agent_call_attempt",
                entity_id=entity_id,
                correlation_id=correlation_id,
                attempt=attempt,
                target="resume_intake",
                url=f"{RESUME_INTAKE_AGENT_URL}/run",
            )

            resp = requests.post(
                f"{RESUME_INTAKE_AGENT_URL}/run",
                json=run_req.model_dump(),
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            break

        except requests.exceptions.RequestException as e:
            last_err = e
            logger.error(
                "agent_call_failed",
                entity_id=entity_id,
                correlation_id=correlation_id,
                attempt=attempt,
                target="resume_intake",
                error=str(e),
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)

    else:
        # All retries exhausted
        logger.error(
            "job_failed",
            entity_id=entity_id,
            correlation_id=correlation_id,
            target="resume_intake",
            error=str(last_err) if last_err else "unknown_error",
        )
        raise HTTPException(status_code=503, detail="resume-intake unavailable")

    # At this point, resp must be a successful HTTP response
    artifact = Artifact.model_validate(resp.json())

    logger.info(
        "job_completed",
        entity_id=entity_id,
        correlation_id=correlation_id,
        artifact_id=artifact.artifact_id,
    )

    return JobResponse(
        job_id=entity_id,
        status="completed",
        artifact_id=artifact.artifact_id,
        correlation_id=correlation_id,
    )
