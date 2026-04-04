from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


STEP_DEFINITIONS: dict[str, dict[str, str]] = {
    "orchestration": {
        "agent": "coordinator",
        "request_message": "Please plan how the coordinator should run this workflow and what each downstream stage should focus on.",
        "response_fallback": "I created a workflow orchestration plan for the downstream agents.",
    },
    "resume-intake": {
        "agent": "resume-intake",
        "request_message": "Please extract the candidate profile from the uploaded resume and normalize the core fields.",
        "response_fallback": "I parsed the resume and returned a structured candidate profile.",
    },
    "skill-assessment": {
        "agent": "skill-assessment",
        "request_message": "Please assess the candidate's skill fit using the parsed resume and job requirements.",
        "response_fallback": "I assessed the candidate's strengths, gaps, and overall skill fit.",
    },
    "screening": {
        "agent": "screening",
        "request_message": "Please score the candidate against the role requirements and decide whether they meet the threshold.",
        "response_fallback": "I scored the candidate and returned a qualification decision.",
    },
    "audit": {
        "agent": "audit",
        "request_message": "Please review the workflow outputs for fairness, compliance, and escalation risk.",
        "response_fallback": "I reviewed the workflow for audit and compliance concerns.",
    },
    "ranking": {
        "agent": "ranking",
        "request_message": "Please rank the candidates for this job using the current decision context.",
        "response_fallback": "I ranked the candidates and returned a recommendation order.",
    },
}

ARTIFACT_TYPE_TO_STAGE = {
    "workflow_orchestration_plan": "orchestration",
    "resume_intake_result": "resume-intake",
    "skill_assessment_result": "skill-assessment",
    "qualification_screening_result": "screening",
    "audit_bias_check_result": "audit",
    "candidate_ranking_result": "ranking",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_stage(*, artifact_type: str | None = None, agent_type: str | None = None) -> str | None:
    if artifact_type and artifact_type in ARTIFACT_TYPE_TO_STAGE:
        return ARTIFACT_TYPE_TO_STAGE[artifact_type]

    if not agent_type:
        return None

    normalized = str(agent_type).replace("_", "-").strip().lower()
    return normalized if normalized in STEP_DEFINITIONS else None


def build_handoff_event(
    *,
    event_id: str,
    timestamp: str,
    entity_id: str | None,
    candidate_id: str | None,
    correlation_id: str | None,
    stage: str,
    direction: str,
    from_agent: str,
    to_agent: str,
    message: str,
    payload_preview: dict[str, Any] | None = None,
    artifact_type: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_kind": "handoff",
        "timestamp": timestamp,
        "entity_id": entity_id,
        "candidate_id": candidate_id,
        "correlation_id": correlation_id,
        "stage": stage,
        "direction": direction,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message": message,
        "payload_preview": payload_preview or {},
        "artifact_type": artifact_type,
        "confidence": confidence,
    }


def build_request_handoff(
    *,
    stage: str,
    entity_id: str,
    candidate_id: str | None,
    correlation_id: str,
    input_data: dict[str, Any] | None,
    timestamp: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    definition = STEP_DEFINITIONS[stage]
    return build_handoff_event(
        event_id=event_id or f"{correlation_id}:{stage}:request",
        timestamp=timestamp or utc_now_iso(),
        entity_id=entity_id,
        candidate_id=candidate_id,
        correlation_id=correlation_id,
        stage=stage,
        direction="request",
        from_agent="coordinator",
        to_agent=definition["agent"],
        message=definition["request_message"],
        payload_preview=_build_request_preview(stage, input_data or {}),
    )


def build_response_handoff(
    *,
    stage: str,
    entity_id: str,
    candidate_id: str | None,
    correlation_id: str,
    artifact_id: str,
    artifact_type: str | None,
    explanation: str | None,
    confidence: float | None,
    payload: Any,
    timestamp: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    definition = STEP_DEFINITIONS[stage]
    return build_handoff_event(
        event_id=event_id or f"{artifact_id}:response",
        timestamp=timestamp or utc_now_iso(),
        entity_id=entity_id,
        candidate_id=candidate_id,
        correlation_id=correlation_id,
        stage=stage,
        direction="response",
        from_agent=definition["agent"],
        to_agent="coordinator",
        message=explanation or definition["response_fallback"],
        payload_preview=_build_response_preview(stage, payload if isinstance(payload, dict) else {}),
        artifact_type=artifact_type,
        confidence=confidence,
    )


def build_handoff_trace(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []

    for row in rows:
        stage = resolve_stage(
            artifact_type=row.get("artifact_type"),
            agent_type=row.get("agent_type"),
        )
        if not stage:
            continue

        artifact_id = str(row.get("artifact_id") or f"{stage}-{len(trace)}")
        entity_id = row.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id:
            continue

        correlation_id = str(row.get("correlation_id") or artifact_id)
        candidate_id = row.get("candidate_id")
        timestamp = _to_timestamp(row.get("created_at"))

        trace.append(
            build_request_handoff(
                stage=stage,
                entity_id=entity_id,
                candidate_id=candidate_id if isinstance(candidate_id, str) else None,
                correlation_id=correlation_id,
                input_data=_historical_request_context(stage, row),
                timestamp=timestamp,
                event_id=f"{artifact_id}:request",
            )
        )
        trace.append(
            build_response_handoff(
                stage=stage,
                entity_id=entity_id,
                candidate_id=candidate_id if isinstance(candidate_id, str) else None,
                correlation_id=correlation_id,
                artifact_id=artifact_id,
                artifact_type=row.get("artifact_type"),
                explanation=row.get("explanation"),
                confidence=_as_float(row.get("confidence")),
                payload=row.get("payload"),
                timestamp=timestamp,
                event_id=f"{artifact_id}:response",
            )
        )

    return trace


def _historical_request_context(stage: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}

    if stage == "resume-intake":
        return {
            "candidate_id": row.get("candidate_id"),
            "requested_fields": ["name", "email", "skills", "years_experience"],
        }
    if stage == "orchestration":
        return {
            "based_on": "job requirements + resume context",
            "job_id": row.get("entity_id"),
        }
    if stage == "skill-assessment":
        return {
            "based_on": "parsed resume + job requirements",
            "parsed_skills_count": len(payload.get("matched_required_skills") or []),
        }
    if stage == "screening":
        return {
            "based_on": "parsed resume + skill assessment",
            "skill_score": _as_float(payload.get("skills_score")),
        }
    if stage == "audit":
        return {
            "based_on": "candidate decisions + workflow stats",
            "candidate_id": row.get("candidate_id"),
        }
    if stage == "ranking":
        ranked_candidates = payload.get("ranked_candidates") if isinstance(payload, dict) else []
        return {
            "based_on": "current candidate decisions",
            "candidate_count": len(ranked_candidates) if isinstance(ranked_candidates, list) else None,
        }
    return {}


def _build_request_preview(stage: str, input_data: dict[str, Any]) -> dict[str, Any]:
    if stage == "orchestration":
        job_requirements = input_data.get("job_requirements") if isinstance(input_data.get("job_requirements"), dict) else {}
        preview = {
            "job_id": input_data.get("job_id"),
            "required_skills": _short_list(job_requirements.get("required_skills")),
            "preferred_skills": _short_list(job_requirements.get("preferred_skills")),
            "resume_text_chars": len(str(input_data.get("resume_text") or "")),
        }
        return _compact(preview)

    if stage == "resume-intake":
        resume_text = str(input_data.get("resume_text") or "")
        job_description = str(input_data.get("job_description") or "")
        preview = {
            "has_resume_url": bool(input_data.get("resume_url")),
            "resume_text_chars": len(resume_text),
            "job_description_chars": len(job_description),
            "requested_fields": ["name", "email", "skills", "years_experience"],
        }
        return _compact(preview)

    if stage == "skill-assessment":
        parsed_resume = input_data.get("parsed_resume") if isinstance(input_data.get("parsed_resume"), dict) else {}
        job_requirements = input_data.get("job_requirements") if isinstance(input_data.get("job_requirements"), dict) else {}
        preview = {
            "parsed_skills": _short_list(parsed_resume.get("skills")),
            "required_skills": _short_list(job_requirements.get("required_skills")),
            "preferred_skills": _short_list(job_requirements.get("preferred_skills")),
            "resume_text_chars": len(str(input_data.get("resume_text") or "")),
        }
        return _compact(preview)

    if stage == "screening":
        parsed_resume = input_data.get("parsed_resume") if isinstance(input_data.get("parsed_resume"), dict) else {}
        job_requirements = input_data.get("job_requirements") if isinstance(input_data.get("job_requirements"), dict) else {}
        skill_assessment = input_data.get("skill_assessment") if isinstance(input_data.get("skill_assessment"), dict) else {}
        preview = {
            "candidate_skills": _short_list(parsed_resume.get("skills")),
            "required_skills": _short_list(job_requirements.get("required_skills")),
            "skill_score": _as_float(skill_assessment.get("skills_score")),
        }
        return _compact(preview)

    if stage == "audit":
        candidates = input_data.get("candidates") if isinstance(input_data.get("candidates"), list) else []
        decisions = input_data.get("decisions") if isinstance(input_data.get("decisions"), list) else []
        stats = input_data.get("stats") if isinstance(input_data.get("stats"), dict) else {}
        preview = {
            "candidate_count": len(candidates),
            "decision_count": len(decisions),
            "shortlisted": stats.get("shortlisted"),
            "review_required": stats.get("review_required"),
        }
        return _compact(preview)

    if stage == "ranking":
        candidates = input_data.get("candidates") if isinstance(input_data.get("candidates"), list) else []
        preview = {
            "candidate_count": len(candidates),
            "job_id": input_data.get("job_id"),
        }
        return _compact(preview)

    return {}


def _build_response_preview(stage: str, payload: dict[str, Any]) -> dict[str, Any]:
    if stage == "orchestration":
        preview = {
            "priority_skills": _short_list(payload.get("priority_skills")),
            "screening_focus": _short_list(payload.get("screening_focus")),
            "audit_focus": _short_list(payload.get("audit_focus")),
            "risk_flags": _short_list(payload.get("risk_flags")),
        }
        return _compact(preview)

    if stage == "resume-intake":
        preview = {
            "name": payload.get("name"),
            "email": payload.get("email"),
            "skills": _short_list(payload.get("skills")),
            "years_experience": payload.get("years_experience"),
        }
        return _compact(preview)

    if stage == "skill-assessment":
        preview = {
            "skills_score": _as_float(payload.get("skills_score")),
            "matched_required_skills": _short_list(payload.get("matched_required_skills")),
            "missing_required_skills": _short_list(payload.get("missing_required_skills")),
            "gaps": _short_list(payload.get("gaps")),
        }
        return _compact(preview)

    if stage == "screening":
        preview = {
            "qualification_score": _as_float(payload.get("qualification_score")),
            "decision": payload.get("decision"),
            "meets_threshold": payload.get("meets_threshold"),
            "needs_human_review": payload.get("needs_human_review"),
        }
        return _compact(preview)

    if stage == "audit":
        preview = {
            "risk_level": payload.get("risk_level"),
            "review_required": payload.get("review_required"),
            "bias_flags": _short_list(payload.get("bias_flags")),
            "recommendations": _short_list(payload.get("recommendations")),
        }
        return _compact(preview)

    if stage == "ranking":
        ranked_candidates = payload.get("ranked_candidates") if isinstance(payload.get("ranked_candidates"), list) else []
        preview = {
            "total_candidates": payload.get("total_candidates") or len(ranked_candidates),
            "top_candidate_id": payload.get("top_candidate_id"),
            "action_breakdown": payload.get("action_breakdown") if isinstance(payload.get("action_breakdown"), dict) else None,
        }
        return _compact(preview)

    return {}


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, item in value.items():
        if item is None:
            continue
        if isinstance(item, str) and not item.strip():
            continue
        if isinstance(item, list) and len(item) == 0:
            continue
        compacted[key] = item
    return compacted


def _short_list(value: Any, limit: int = 4) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_timestamp(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return utc_now_iso()
