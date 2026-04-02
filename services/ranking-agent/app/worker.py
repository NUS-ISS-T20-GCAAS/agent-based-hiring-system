from typing import Any, Optional


ACTION_INVITE = "INVITE_TO_INTERVIEW"
ACTION_HOLD = "HOLD_FOR_REVIEW"
ACTION_REJECT = "REJECT"


def heuristic_rank_candidates(
    *,
    candidates: list[dict[str, Any]],
    top_k: Optional[int] = None,
) -> dict[str, Any]:
    ranked_candidates: list[dict[str, Any]] = []

    for candidate in candidates:
        scores = candidate.get("scores") if isinstance(candidate.get("scores"), dict) else {}
        qualification = _to_float(scores.get("qualification"), candidate.get("qualification_score"))
        skills = _to_float(scores.get("skills"), candidate.get("skills_score"))
        composite = _to_float(scores.get("composite"), candidate.get("composite_score"))
        needs_human_review = bool(candidate.get("needs_human_review"))
        recommendation = str(candidate.get("recommendation") or "PENDING").upper()
        status = str(candidate.get("status") or "processing").lower()
        review_reasons = _string_list(candidate.get("review_reasons"))

        if composite == 0.0:
            composite = round((qualification * 0.7) + (skills * 0.3), 4)

        ranking_score = _compute_ranking_score(
            composite=composite,
            qualification=qualification,
            skills=skills,
            recommendation=recommendation,
            needs_human_review=needs_human_review,
        )
        recommended_action = _recommended_action(
            status=status,
            recommendation=recommendation,
            needs_human_review=needs_human_review,
            ranking_score=ranking_score,
            qualification=qualification,
            skills=skills,
        )
        decision_factors = _decision_factors(
            qualification=qualification,
            skills=skills,
            recommendation=recommendation,
            needs_human_review=needs_human_review,
            review_reasons=review_reasons,
            recommended_action=recommended_action,
        )
        ranking_summary = _ranking_summary(
            candidate_name=candidate.get("name") or "Unknown Candidate",
            recommended_action=recommended_action,
            ranking_score=ranking_score,
            decision_factors=decision_factors,
        )

        ranked_candidates.append(
            {
                "candidate_id": candidate.get("id") or candidate.get("candidate_id"),
                "name": candidate.get("name") or "Unknown Candidate",
                "recommendation": recommendation,
                "status": status,
                "score": ranking_score,
                "scores": {
                    "qualification": qualification,
                    "skills": skills,
                    "composite": composite,
                },
                "recommended_action": recommended_action,
                "decision_factors": decision_factors,
                "ranking_summary": ranking_summary,
                "review_state": {
                    "needs_human_review": needs_human_review,
                    "review_reasons": review_reasons,
                },
            }
        )

    ranked_candidates.sort(key=lambda item: item["score"], reverse=True)

    for index, item in enumerate(ranked_candidates, start=1):
        item["rank"] = index

    if top_k is not None and top_k > 0:
        ranked_candidates = ranked_candidates[:top_k]

    top_candidate_id = ranked_candidates[0]["candidate_id"] if ranked_candidates else None
    avg_score = (
        round(sum(item["score"] for item in ranked_candidates) / len(ranked_candidates), 4)
        if ranked_candidates
        else 0.0
    )
    action_breakdown = {
        "invite_to_interview": sum(1 for item in ranked_candidates if item["recommended_action"] == ACTION_INVITE),
        "hold_for_review": sum(1 for item in ranked_candidates if item["recommended_action"] == ACTION_HOLD),
        "reject": sum(1 for item in ranked_candidates if item["recommended_action"] == ACTION_REJECT),
    }

    return {
        "ranked_candidates": ranked_candidates,
        "top_candidate_id": top_candidate_id,
        "avg_score": avg_score,
        "total_candidates": len(ranked_candidates),
        "action_breakdown": action_breakdown,
        "method": "heuristic_weighted_recommendation",
    }


def _to_float(*values: Any) -> float:
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _compute_ranking_score(
    *,
    composite: float,
    qualification: float,
    skills: float,
    recommendation: str,
    needs_human_review: bool,
) -> float:
    recommendation_adjustment = {
        "SHORTLIST": 0.06,
        "CONSIDER": 0.02,
        "PENDING": 0.0,
        "REJECT": -0.08,
    }.get(recommendation, 0.0)
    review_adjustment = -0.05 if needs_human_review else 0.0
    quality_adjustment = (qualification * 0.05) + (skills * 0.03)
    ranking_score = composite + recommendation_adjustment + review_adjustment + quality_adjustment
    return round(max(0.0, min(1.0, ranking_score)), 4)


def _recommended_action(
    *,
    status: str,
    recommendation: str,
    needs_human_review: bool,
    ranking_score: float,
    qualification: float,
    skills: float,
) -> str:
    if recommendation == "REJECT" or status == "rejected":
        return ACTION_REJECT
    if needs_human_review:
        return ACTION_HOLD
    if ranking_score >= 0.78 and qualification >= 0.7 and skills >= 0.65:
        return ACTION_INVITE
    if recommendation in {"SHORTLIST", "CONSIDER"} or ranking_score >= 0.58:
        return ACTION_HOLD
    return ACTION_REJECT


def _decision_factors(
    *,
    qualification: float,
    skills: float,
    recommendation: str,
    needs_human_review: bool,
    review_reasons: list[str],
    recommended_action: str,
) -> list[str]:
    factors: list[str] = []

    if qualification >= 0.8:
        factors.append("strong qualification score")
    elif qualification >= 0.65:
        factors.append("acceptable qualification score")
    else:
        factors.append("qualification score below ideal range")

    if skills >= 0.75:
        factors.append("strong skill alignment")
    elif skills >= 0.55:
        factors.append("partial skill alignment")
    else:
        factors.append("skill gaps remain")

    if recommendation == "SHORTLIST":
        factors.append("screening recommends shortlist")
    elif recommendation == "CONSIDER":
        factors.append("screening recommends consideration")
    elif recommendation == "REJECT":
        factors.append("screening recommends rejection")

    if needs_human_review:
        if review_reasons:
            factors.append(f"human review required: {review_reasons[0]}")
        else:
            factors.append("human review required")
    elif recommended_action == ACTION_INVITE:
        factors.append("no review blockers detected")

    return factors[:5]


def _ranking_summary(
    *,
    candidate_name: str,
    recommended_action: str,
    ranking_score: float,
    decision_factors: list[str],
) -> str:
    headline = (
        f"{candidate_name} is recommended for interview"
        if recommended_action == ACTION_INVITE
        else f"{candidate_name} should be held for review"
        if recommended_action == ACTION_HOLD
        else f"{candidate_name} is not recommended for the shortlist"
    )
    if not decision_factors:
        return f"{headline} with ranking score {ranking_score:.1%}."
    return f"{headline} with ranking score {ranking_score:.1%}. Key factors: {', '.join(decision_factors[:3])}."
