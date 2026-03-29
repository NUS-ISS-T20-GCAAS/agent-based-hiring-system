from typing import Any, Optional


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

        if composite == 0.0:
            composite = round((qualification * 0.7) + (skills * 0.3), 4)

        ranked_candidates.append(
            {
                "candidate_id": candidate.get("id") or candidate.get("candidate_id"),
                "name": candidate.get("name") or "Unknown Candidate",
                "recommendation": candidate.get("recommendation") or "PENDING",
                "score": composite,
                "scores": {
                    "qualification": qualification,
                    "skills": skills,
                    "composite": composite,
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

    return {
        "ranked_candidates": ranked_candidates,
        "top_candidate_id": top_candidate_id,
        "avg_score": avg_score,
        "total_candidates": len(ranked_candidates),
        "method": "heuristic_composite_score",
    }


def _to_float(*values: Any) -> float:
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0
