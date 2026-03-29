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
                "details": {
                    "method": ranking["method"],
                    "top_k": top_k,
                },
            },
            "confidence": 0.6 if ranking["ranked_candidates"] else 0.4,
            "explanation": explanation,
        }

    def _build_explanation(self, ranking: dict) -> str:
        if not ranking["ranked_candidates"]:
            return "No candidates available to rank"

        leader = ranking["ranked_candidates"][0]
        return (
            f"Ranked {ranking['total_candidates']} candidates using {ranking['method']}; "
            f"top candidate={leader['name']} score={leader['score']:.1%}"
        )
