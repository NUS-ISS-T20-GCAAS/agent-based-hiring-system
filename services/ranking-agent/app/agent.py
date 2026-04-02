from app.base_agent import BaseAgent
from app.worker import heuristic_rank_candidates


class RankingAgent(BaseAgent):
    def artifact_type(self) -> str:
        return "candidate_ranking_result"

    def handle(self, input_data):
        candidates = input_data.get("candidates") or []
        top_k = input_data.get("top_k")
        ranking = heuristic_rank_candidates(candidates=candidates, top_k=top_k)

        explanation = self._build_explanation(ranking)
        return {
            "payload": {
                "job_id": input_data.get("job_id"),
                "ranked_candidates": ranking["ranked_candidates"],
                "top_candidate_id": ranking["top_candidate_id"],
                "total_candidates": ranking["total_candidates"],
                "avg_score": ranking["avg_score"],
                "action_breakdown": ranking["action_breakdown"],
                "details": {
                    "method": ranking["method"],
                    "top_k": top_k,
                },
            },
            "confidence": self._confidence(ranking),
            "explanation": explanation,
        }

    def _build_explanation(self, ranking: dict) -> str:
        if not ranking["ranked_candidates"]:
            return "No candidates available to rank"

        leader = ranking["ranked_candidates"][0]
        return (
            f"Ranked {ranking['total_candidates']} candidates using {ranking['method']}. "
            f"Top candidate: {leader['name']} at {leader['score']:.1%} with action {leader['recommended_action']}. "
            f"Action mix: invite={ranking['action_breakdown']['invite_to_interview']}, "
            f"hold={ranking['action_breakdown']['hold_for_review']}, "
            f"reject={ranking['action_breakdown']['reject']}."
        )

    def _confidence(self, ranking: dict) -> float:
        total = ranking["total_candidates"]
        if total == 0:
            return 0.4
        if ranking["action_breakdown"]["hold_for_review"] > 0:
            return 0.68
        return 0.78
