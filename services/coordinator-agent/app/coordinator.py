import uuid
import time
from datetime import date, datetime
from decimal import Decimal
import requests
from fastapi import HTTPException

from app.schemas import JobRequest, JobResponse, RunRequest, Artifact
from app.logger import get_logger
from app.config import AUDIT_AGENT_URL, RESUME_INTAKE_AGENT_URL, SCREENING_AGENT_URL, REQUEST_TIMEOUT
from app.repository import CoordinatorRepository

logger = get_logger("coordinator")

MAX_RETRIES = 3
RETRY_DELAY_SEC = 0.5


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


def _screening_status(screening_payload: dict | None) -> tuple[str, str]:
    screening_payload = screening_payload or {}
    meets_threshold = bool(screening_payload.get("meets_threshold"))
    recommendation = "SHORTLIST" if meets_threshold else "REJECT"
    status = "shortlisted" if meets_threshold else "rejected"
    return status, recommendation


def _normalize_reason(reason: object) -> str | None:
    if not isinstance(reason, str):
        return None
    normalized = " ".join(reason.strip().split())
    return normalized or None


def _dedupe_reasons(reasons: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        deduped.append(reason)
    return deduped


def _build_review_state(
    screening_payload: dict | None,
    audit_payload: dict | None,
) -> dict:
    screening_payload = screening_payload or {}
    audit_payload = audit_payload or {}

    screening_required = bool(screening_payload.get("needs_human_review"))
    audit_required = bool(audit_payload.get("review_required"))

    reasons: list[str] = []

    if screening_required:
        screening_reasons = screening_payload.get("review_reasons")
        if isinstance(screening_reasons, list):
            for item in screening_reasons:
                normalized = _normalize_reason(item)
                if normalized:
                    reasons.append(f"Screening: {normalized}")
        if not reasons:
            reasons.append("Screening: candidate requires manual review")

    if audit_required:
        audit_flags = audit_payload.get("bias_flags")
        if isinstance(audit_flags, list):
            for flag in audit_flags:
                normalized = _normalize_reason(str(flag).replace("_", " "))
                if normalized:
                    reasons.append(f"Audit: {normalized}")

        if not any(reason.startswith("Audit:") for reason in reasons):
            risk_level = _normalize_reason(audit_payload.get("risk_level"))
            if risk_level:
                reasons.append(f"Audit: risk level {risk_level}")
            else:
                reasons.append("Audit: workflow requires compliance review")

    needs_human_review = screening_required or audit_required
    if screening_required and audit_required:
        escalation_source = "screening_and_audit"
    elif screening_required:
        escalation_source = "screening"
    elif audit_required:
        escalation_source = "audit"
    else:
        escalation_source = "none"

    return {
        "needs_human_review": needs_human_review,
        "review_status": "pending" if needs_human_review else "not_required",
        "review_reasons": _dedupe_reasons(reasons),
        "escalation_source": escalation_source,
    }


def _build_audit_input(
    *,
    repository: CoordinatorRepository,
    job_id: str,
    candidate_id: str,
    screening_payload: dict | None,
) -> dict:
    screening_payload = screening_payload if isinstance(screening_payload, dict) else {}
    candidate_status, recommendation = _screening_status(screening_payload)

    stats = repository.get_stats(job_id=job_id)
    if screening_payload.get("meets_threshold"):
        stats = {
            **stats,
            "shortlisted": int(stats.get("shortlisted") or 0) + 1,
        }

    candidates = repository.list_candidates(job_id=job_id)
    patched_candidates: list[dict] = []
    for row in candidates:
        candidate = dict(row)
        if candidate.get("id") == candidate_id:
            candidate["status"] = candidate_status
            candidate["recommendation"] = recommendation
            candidate["scores"] = {
                "qualification": screening_payload.get("qualification_score") or 0.0,
                "skills": candidate.get("skills_score") or 0.0,
                "composite": candidate.get("composite_score") or 0.0,
            }
        patched_candidates.append(candidate)

    decisions = repository.list_artifacts(job_id=job_id)

    return {
        "job_id": job_id,
        "stats": stats,
        "candidates": patched_candidates,
        "decisions": decisions,
    }


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
                json=_json_safe(run_req.model_dump()),
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

        current_step = "audit"
        repository.update_workflow_step(run_id=run_id, current_step=current_step)

        audit_request = RunRequest(
            entity_id=entity_id,
            correlation_id=correlation_id,
            input_data=_build_audit_input(
                repository=repository,
                job_id=entity_id,
                candidate_id=candidate_id,
                screening_payload=screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
            ),
        )

        audit_artifact = _post_with_retries(
            target="audit",
            url=f"{AUDIT_AGENT_URL}/run",
            run_req=audit_request,
            entity_id=entity_id,
            correlation_id=correlation_id,
        )
        repository.save_artifact(
            job_id=entity_id,
            candidate_id=candidate_id,
            artifact=audit_artifact,
        )
        review_state = _build_review_state(
            screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
            audit_artifact.payload if isinstance(audit_artifact.payload, dict) else None,
        )
        repository.complete_workflow(
            job_id=entity_id,
            candidate_id=candidate_id,
            run_id=run_id,
            intake_payload=intake_artifact.payload if isinstance(intake_artifact.payload, dict) else None,
            screening_payload=screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
            review_state=review_state,
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
        artifacts=[intake_artifact.artifact_id, screening_artifact.artifact_id, audit_artifact.artifact_id],
    )

    return JobResponse(
        job_id=entity_id,
        status="completed",
        artifact_id=audit_artifact.artifact_id,
        correlation_id=correlation_id,
    )
