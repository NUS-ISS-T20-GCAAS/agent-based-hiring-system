import uuid
import time
import requests
from fastapi import HTTPException

from app.schemas import JobRequest, JobResponse, RunRequest, Artifact
from app.logger import get_logger
from app.config import RESUME_INTAKE_AGENT_URL, SCREENING_AGENT_URL, REQUEST_TIMEOUT

logger = get_logger("coordinator")

MAX_RETRIES = 3
RETRY_DELAY_SEC = 0.5


def _post_with_retries(
    *,
    target: str,
    url: str,
    run_req: RunRequest,
    entity_id: str,
    correlation_id: str,
) -> Artifact:
    last_err: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "agent_call_attempt",
                entity_id=entity_id,
                correlation_id=correlation_id,
                attempt=attempt,
                target=target,
                url=url,
            )

            resp = requests.post(
                url,
                json=run_req.model_dump(),
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return Artifact.model_validate(resp.json())

        except requests.exceptions.RequestException as exc:
            last_err = exc
            logger.error(
                "agent_call_failed",
                entity_id=entity_id,
                correlation_id=correlation_id,
                attempt=attempt,
                target=target,
                error=str(exc),
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)

    logger.error(
        "job_failed",
        entity_id=entity_id,
        correlation_id=correlation_id,
        target=target,
        error=str(last_err) if last_err else "unknown_error",
    )
    raise HTTPException(status_code=503, detail=f"{target} unavailable")


def run_job(request: JobRequest) -> JobResponse:
    entity_id = request.job_id
    correlation_id = str(uuid.uuid4())

    logger.info("job_received", entity_id=entity_id, correlation_id=correlation_id)

    intake_request = RunRequest(
        entity_id=entity_id,
        correlation_id=correlation_id,
        input_data={
            "resume_url": request.resume_url,
            "job_description": request.job_description,
            "resume_text": request.resume_text,
        },
    )

    intake_artifact = _post_with_retries(
        target="resume-intake",
        url=f"{RESUME_INTAKE_AGENT_URL}/run",
        run_req=intake_request,
        entity_id=entity_id,
        correlation_id=correlation_id,
    )

    screening_request = RunRequest(
        entity_id=entity_id,
        correlation_id=correlation_id,
        input_data={
            "job_description": request.job_description,
            "parsed_resume": intake_artifact.payload,
        },
    )

    screening_artifact = _post_with_retries(
        target="screening",
        url=f"{SCREENING_AGENT_URL}/run",
        run_req=screening_request,
        entity_id=entity_id,
        correlation_id=correlation_id,
    )

    logger.info(
        "job_completed",
        entity_id=entity_id,
        correlation_id=correlation_id,
        artifacts=[intake_artifact.artifact_id, screening_artifact.artifact_id],
    )

    return JobResponse(
        job_id=entity_id,
        status="completed",
        artifact_id=screening_artifact.artifact_id,
        correlation_id=correlation_id,
    )
