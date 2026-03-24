from app.config import LOW_SELECTION_RATE_THRESHOLD, MIN_AUDIT_SAMPLE_SIZE


def heuristic_audit_check(
    *,
    job_id: str | None,
    stats: dict,
    candidates: list[dict],
    decisions: list[dict],
) -> dict:
    total_candidates = int(stats.get("total_candidates") or len(candidates) or 0)
    shortlisted = int(stats.get("shortlisted") or 0)
    if shortlisted == 0 and candidates:
        shortlisted = sum(1 for c in candidates if str(c.get("status", "")).lower() == "shortlisted")

    selection_rate = 0.0 if total_candidates == 0 else shortlisted / total_candidates
    bias_flags: list[str] = []
    recommendations: list[str] = []

    if total_candidates == 0:
        bias_flags.append("insufficient_data")
        recommendations.append("Collect candidate outcomes before running audit checks.")

    if 0 < total_candidates < MIN_AUDIT_SAMPLE_SIZE:
        bias_flags.append("small_sample_size")
        recommendations.append("Treat audit output as directional only until more candidates are processed.")

    if total_candidates > 0 and selection_rate < LOW_SELECTION_RATE_THRESHOLD:
        bias_flags.append("low_selection_rate")
        recommendations.append("Review screening thresholds and shortlisted decision criteria.")

    if decisions and not any(str(d.get("decision_type", "")).endswith("result") for d in decisions):
        bias_flags.append("incomplete_decision_trail")
        recommendations.append("Ensure all candidate decisions are persisted before audit review.")

    if not recommendations:
        recommendations.append("No immediate audit action required; continue monitoring outcomes.")

    risk_level = "high" if "low_selection_rate" in bias_flags else "medium" if bias_flags else "low"
    review_required = bool(bias_flags)
    data_completeness = 0.0 if total_candidates == 0 else min(1.0, len(decisions) / max(total_candidates, 1))
    confidence = 0.55 if total_candidates == 0 else min(0.9, 0.6 + (0.05 * min(total_candidates, 6)))

    return {
        "job_id": job_id,
        "selection_rate": round(selection_rate, 4),
        "total_candidates": total_candidates,
        "shortlisted": shortlisted,
        "bias_flags": bias_flags,
        "risk_level": risk_level,
        "review_required": review_required,
        "recommendations": recommendations,
        "data_completeness": round(data_completeness, 4),
        "confidence": round(confidence, 2),
    }


def coerce_audit_result(result: dict) -> dict:
    bias_flags = result.get("bias_flags")
    recommendations = result.get("recommendations")
    risk_level = str(result.get("risk_level") or "medium").lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = "medium"

    try:
        selection_rate = float(result.get("selection_rate") or 0.0)
    except (TypeError, ValueError):
        selection_rate = 0.0

    try:
        confidence = float(result.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.5

    try:
        data_completeness = float(result.get("data_completeness") or 0.0)
    except (TypeError, ValueError):
        data_completeness = 0.0

    return {
        "job_id": result.get("job_id"),
        "selection_rate": max(0.0, min(1.0, selection_rate)),
        "total_candidates": int(result.get("total_candidates") or 0),
        "shortlisted": int(result.get("shortlisted") or 0),
        "bias_flags": bias_flags if isinstance(bias_flags, list) else [],
        "risk_level": risk_level,
        "review_required": bool(result.get("review_required")),
        "recommendations": recommendations if isinstance(recommendations, list) else [],
        "data_completeness": max(0.0, min(1.0, data_completeness)),
        "confidence": max(0.0, min(1.0, confidence)),
    }
