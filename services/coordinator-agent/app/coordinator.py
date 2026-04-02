import uuid
import time
from datetime import date, datetime
from decimal import Decimal
import requests
from fastapi import HTTPException

from app.events import emit_agent_activity, emit_candidate_update
from app.handoff_trace import build_request_handoff, build_response_handoff
from app.schemas import JobRequest, JobResponse, RunRequest, Artifact
from app.logger import get_logger
from app.config import (
    AUDIT_AGENT_URL,
    RESUME_INTAKE_AGENT_URL,
    SCREENING_AGENT_URL,
    SKILL_ASSESSMENT_AGENT_URL,
    REQUEST_TIMEOUT,
)
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


def _skill_score(skill_assessment_payload: dict | None, screening_payload: dict | None) -> float:
    skill_assessment_payload = skill_assessment_payload or {}
    screening_payload = screening_payload or {}

    try:
        score = float(skill_assessment_payload.get("skills_score"))
        return max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        pass

    matched = screening_payload.get("matched_skills") or []
    missing = screening_payload.get("missing_skills") or []
    denominator = len(matched) + len(missing)
    return 0.0 if denominator == 0 else len(matched) / denominator


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
    skill_assessment_payload: dict | None,
    screening_payload: dict | None,
) -> dict:
    screening_payload = screening_payload if isinstance(screening_payload, dict) else {}
    skill_assessment_payload = skill_assessment_payload if isinstance(skill_assessment_payload, dict) else {}
    candidate_status, recommendation = _screening_status(screening_payload)
    skill_score = _skill_score(skill_assessment_payload, screening_payload)
    qualification_score = float(screening_payload.get("qualification_score") or 0.0)
    composite_score = round((qualification_score * 0.7) + (skill_score * 0.3), 4)

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
                "qualification": qualification_score,
                "skills": skill_score,
                "composite": composite_score,
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


def _emit_handoff_trace(event: dict) -> None:
    emit_agent_activity(
        agent=event.get("from_agent") or event.get("to_agent") or "coordinator",
        message=event.get("message") or "",
        correlation_id=event.get("correlation_id"),
        entity_id=event.get("entity_id"),
        candidate_id=event.get("candidate_id"),
        event_id=event.get("event_id"),
        event_kind=event.get("event_kind"),
        stage=event.get("stage"),
        direction=event.get("direction"),
        from_agent=event.get("from_agent"),
        to_agent=event.get("to_agent"),
        artifact_type=event.get("artifact_type"),
        payload_preview=event.get("payload_preview"),
        confidence=event.get("confidence"),
    )


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
        emit_agent_activity(
            agent="coordinator",
            message=f"Started workflow for job {entity_id}",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        emit_candidate_update(
            job_id=entity_id,
            candidate_id=candidate_id,
            status="processing",
            correlation_id=correlation_id,
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
        emit_agent_activity(
            agent="resume-intake",
            message=f"Starting resume intake for job {entity_id}",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        _emit_handoff_trace(
            build_request_handoff(
                stage="resume-intake",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                input_data=intake_request.input_data,
            )
        )
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
        _emit_handoff_trace(
            build_response_handoff(
                stage="resume-intake",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                artifact_id=intake_artifact.artifact_id,
                artifact_type=intake_artifact.artifact_type,
                explanation=intake_artifact.explanation,
                confidence=intake_artifact.confidence,
                payload=intake_artifact.payload,
                timestamp=intake_artifact.created_at,
            )
        )
        emit_agent_activity(
            agent="resume-intake",
            message="Resume intake completed",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )

        current_step = "skill-assessment"
        repository.update_workflow_step(run_id=run_id, current_step=current_step)

        skill_assessment_request = RunRequest(
            entity_id=entity_id,
            correlation_id=correlation_id,
            input_data={
                "job_description": request.job_description,
                "parsed_resume": intake_artifact.payload,
                "resume_text": request.resume_text,
                "job_requirements": job_requirements,
            },
        )

        emit_agent_activity(
            agent="skill-assessment",
            message="Starting skill assessment",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        _emit_handoff_trace(
            build_request_handoff(
                stage="skill-assessment",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                input_data=skill_assessment_request.input_data,
            )
        )
        skill_assessment_artifact = _post_with_retries(
            target="skill-assessment",
            url=f"{SKILL_ASSESSMENT_AGENT_URL}/run",
            run_req=skill_assessment_request,
            entity_id=entity_id,
            correlation_id=correlation_id,
        )
        repository.save_artifact(
            job_id=entity_id,
            candidate_id=candidate_id,
            artifact=skill_assessment_artifact,
        )
        _emit_handoff_trace(
            build_response_handoff(
                stage="skill-assessment",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                artifact_id=skill_assessment_artifact.artifact_id,
                artifact_type=skill_assessment_artifact.artifact_type,
                explanation=skill_assessment_artifact.explanation,
                confidence=skill_assessment_artifact.confidence,
                payload=skill_assessment_artifact.payload,
                timestamp=skill_assessment_artifact.created_at,
            )
        )
        emit_agent_activity(
            agent="skill-assessment",
            message="Skill assessment completed",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
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
                "skill_assessment": skill_assessment_artifact.payload,
            },
        )

        emit_agent_activity(
            agent="screening",
            message="Starting qualification screening",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        _emit_handoff_trace(
            build_request_handoff(
                stage="screening",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                input_data=screening_request.input_data,
            )
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
        _emit_handoff_trace(
            build_response_handoff(
                stage="screening",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                artifact_id=screening_artifact.artifact_id,
                artifact_type=screening_artifact.artifact_type,
                explanation=screening_artifact.explanation,
                confidence=screening_artifact.confidence,
                payload=screening_artifact.payload,
                timestamp=screening_artifact.created_at,
            )
        )
        emit_agent_activity(
            agent="screening",
            message="Qualification screening completed",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
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
                skill_assessment_payload=skill_assessment_artifact.payload if isinstance(skill_assessment_artifact.payload, dict) else None,
                screening_payload=screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
            ),
        )

        emit_agent_activity(
            agent="audit",
            message="Starting audit review",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        _emit_handoff_trace(
            build_request_handoff(
                stage="audit",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                input_data=audit_request.input_data,
            )
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
        _emit_handoff_trace(
            build_response_handoff(
                stage="audit",
                entity_id=entity_id,
                candidate_id=candidate_id,
                correlation_id=correlation_id,
                artifact_id=audit_artifact.artifact_id,
                artifact_type=audit_artifact.artifact_type,
                explanation=audit_artifact.explanation,
                confidence=audit_artifact.confidence,
                payload=audit_artifact.payload,
                timestamp=audit_artifact.created_at,
            )
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
            skill_payload=skill_assessment_artifact.payload if isinstance(skill_assessment_artifact.payload, dict) else None,
            screening_payload=screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
            review_state=review_state,
        )
        emit_agent_activity(
            agent="audit",
            message="Audit review completed",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        emit_agent_activity(
            agent="coordinator",
            message="Workflow completed successfully",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        final_status, _recommendation = _screening_status(
            screening_artifact.payload if isinstance(screening_artifact.payload, dict) else None,
        )
        emit_candidate_update(
            job_id=entity_id,
            candidate_id=candidate_id,
            status=final_status,
            correlation_id=correlation_id,
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
        emit_agent_activity(
            agent="coordinator",
            message=f"Workflow failed during {current_step}: {exc.detail}",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        emit_candidate_update(
            job_id=entity_id,
            candidate_id=candidate_id,
            status="rejected",
            correlation_id=correlation_id,
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
        emit_agent_activity(
            agent="coordinator",
            message=f"Workflow failed during {current_step}: {exc}",
            correlation_id=correlation_id,
            entity_id=entity_id,
            candidate_id=candidate_id,
        )
        emit_candidate_update(
            job_id=entity_id,
            candidate_id=candidate_id,
            status="rejected",
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=500, detail="coordinator execution failed")

    logger.info(
        "job_completed",
        entity_id=entity_id,
        correlation_id=correlation_id,
        candidate_id=candidate_id,
        artifacts=[
            intake_artifact.artifact_id,
            skill_assessment_artifact.artifact_id,
            screening_artifact.artifact_id,
            audit_artifact.artifact_id,
        ],
    )

    return JobResponse(
        job_id=entity_id,
        status="completed",
        artifact_id=audit_artifact.artifact_id,
        correlation_id=correlation_id,
    )
