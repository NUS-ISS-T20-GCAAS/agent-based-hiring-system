import uuid
import time
import requests
from fastapi import HTTPException

from app.schemas import JobRequest, JobResponse, RunRequest, Artifact
from app.logger import get_logger
from app.config import RESUME_INTAKE_AGENT_URL, SCREENING_AGENT_URL, REQUEST_TIMEOUT
from app.repository import CoordinatorRepository

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


def run_job(
    request: JobRequest,
    repository: CoordinatorRepository | None = None,
) -> JobResponse:
    repository = repository or CoordinatorRepository()

    entity_id = request.job_id
    correlation_id = str(uuid.uuid4())
    job_requirements = {
        "required_skills": request.required_skills,
        "preferred_skills": request.preferred_skills,
        "min_years_experience": request.min_years_experience,
        "education_level": request.education_level,
    }

    logger.info("job_received", entity_id=entity_id, correlation_id=correlation_id)

    try:
        repository.upsert_job(
            job_id=entity_id,
            job_description=request.job_description,
            job_requirements=job_requirements,
        )
        candidate_id = repository.create_candidate(
            job_id=entity_id,
            resume_url=request.resume_url,
            resume_text=request.resume_text,
            correlation_id=correlation_id,
        )
        run_id = repository.start_workflow_run(
            job_id=entity_id,
            candidate_id=candidate_id,
            correlation_id=correlation_id,
            current_step="resume-intake",
        )
    except Exception as exc:
        logger.error(
            "job_persist_bootstrap_failed",
            entity_id=entity_id,
            correlation_id=correlation_id,
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail="database unavailable")

    intake_request = RunRequest(
        entity_id=entity_id,
        correlation_id=correlation_id,
        input_data={
            "resume_url": request.resume_url,
            "job_description": request.job_description,
            "resume_text": request.resume_text,
        },
    )

    current_step = "resume-intake"
    try:
        intake_artifact = _post_with_retries(
            target="resume-intake",
            url=f"{RESUME_INTAKE_AGENT_URL}/run",
            run_req=intake_request,
            entity_id=entity_id,
            correlation_id=correlation_id,
        )
        repository.save_artifact(
            job_id=entity_id,
            candidate_id=candidate_id,
            artifact=intake_artifact,
        )

        current_step = "screening"
        repository.update_workflow_step(run_id=run_id, current_step=current_step)

        screening_request = RunRequest(
            entity_id=entity_id,
            correlation_id=correlation_id,
            input_data={
                "job_description": request.job_description,
                "parsed_resume": intake_artifact.payload,
                "job_requirements": job_requirements,
            },
        )

        screening_artifact = _post_with_retries(
            target="screening",
            url=f"{SCREENING_AGENT_URL}/run",
            run_req=screening_request,
            entity_id=entity_id,
            correlation_id=correlation_id,
        )
        repository.save_artifact(
            job_id=entity_id,
            candidate_id=candidate_id,
            artifact=screening_artifact,
        )
        repository.complete_workflow(
            job_id=entity_id,
            candidate_id=candidate_id,
            run_id=run_id,
            intake_payload=intake_artifact.payload if isinstance(intake_artifact.payload, dict) else None,
            screening_payload=screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
        )
    except HTTPException as exc:
        try:
            repository.mark_workflow_failed(
                job_id=entity_id,
                run_id=run_id,
                candidate_id=candidate_id,
                step=current_step,
                error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            )
        except Exception as persist_exc:
            logger.error(
                "job_persist_failure_update_failed",
                entity_id=entity_id,
                correlation_id=correlation_id,
                error=str(persist_exc),
            )
        raise
    except Exception as exc:
        try:
            repository.mark_workflow_failed(
                job_id=entity_id,
                run_id=run_id,
                candidate_id=candidate_id,
                step=current_step,
                error=str(exc),
            )
        except Exception as persist_exc:
            logger.error(
                "job_persist_failure_update_failed",
                entity_id=entity_id,
                correlation_id=correlation_id,
                error=str(persist_exc),
            )
        raise HTTPException(status_code=500, detail="coordinator execution failed")

    logger.info(
        "job_completed",
        entity_id=entity_id,
        correlation_id=correlation_id,
        candidate_id=candidate_id,
        artifacts=[intake_artifact.artifact_id, screening_artifact.artifact_id],
    )

    return JobResponse(
        job_id=entity_id,
        status="completed",
        artifact_id=screening_artifact.artifact_id,
        correlation_id=correlation_id,
    )
