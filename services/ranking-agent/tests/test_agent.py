import unittest

from app.agent import RankingAgent
from app.shared_memory import SharedMemory
from app.worker import heuristic_rank_candidates


class RankingWorkerTests(unittest.TestCase):
    def test_ranks_candidates_by_composite_score(self):
        result = heuristic_rank_candidates(
            candidates=[
                {"id": "c-1", "name": "Alice", "scores": {"composite": 0.82}},
                {"id": "c-2", "name": "Bob", "scores": {"composite": 0.65}},
            ]
        )

        self.assertEqual(result["top_candidate_id"], "c-1")
        self.assertEqual(result["ranked_candidates"][0]["rank"], 1)
        self.assertEqual(result["ranked_candidates"][1]["rank"], 2)
        self.assertEqual(result["ranked_candidates"][0]["recommended_action"], "HOLD_FOR_REVIEW")

    def test_falls_back_to_weighted_scores(self):
        result = heuristic_rank_candidates(
            candidates=[
                {"id": "c-1", "scores": {"qualification": 0.7, "skills": 0.5}},
            ]
        )

        self.assertAlmostEqual(result["ranked_candidates"][0]["score"], 0.69)
        self.assertEqual(result["ranked_candidates"][0]["recommended_action"], "HOLD_FOR_REVIEW")

    def test_rejects_when_candidate_is_rejected_and_review_not_needed(self):
        result = heuristic_rank_candidates(
            candidates=[
                {
                    "id": "c-1",
                    "name": "Alice",
                    "status": "rejected",
                    "recommendation": "REJECT",
                    "scores": {"qualification": 0.42, "skills": 0.3, "composite": 0.39},
                },
                {
                    "id": "c-2",
                    "name": "Bob",
                    "status": "shortlisted",
                    "recommendation": "SHORTLIST",
                    "scores": {"qualification": 0.84, "skills": 0.76, "composite": 0.81},
                },
            ]
        )

        self.assertEqual(result["ranked_candidates"][0]["candidate_id"], "c-2")
        self.assertEqual(result["ranked_candidates"][0]["recommended_action"], "INVITE_TO_INTERVIEW")
        self.assertEqual(result["ranked_candidates"][1]["recommended_action"], "REJECT")
        self.assertEqual(result["action_breakdown"]["invite_to_interview"], 1)
        self.assertEqual(result["action_breakdown"]["reject"], 1)


class RankingAgentTests(unittest.TestCase):
    def test_builds_ranking_artifact_payload(self):
        agent = RankingAgent(agent_type="ranking", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "job_id": "job-1",
                "candidates": [
                    {"id": "c-1", "name": "Alice", "scores": {"composite": 0.88}},
                    {"id": "c-2", "name": "Bob", "scores": {"composite": 0.55}},
                ],
                "top_k": 1,
            }
        )

        self.assertEqual(result["payload"]["job_id"], "job-1")
        self.assertEqual(result["payload"]["total_candidates"], 1)
        self.assertEqual(result["payload"]["top_candidate_id"], "c-1")
        self.assertEqual(result["payload"]["details"]["method"], "heuristic_weighted_recommendation")
        self.assertIn("action_breakdown", result["payload"])
        self.assertIn("recommended_action", result["payload"]["ranked_candidates"][0])
        self.assertIn("ranking score", result["payload"]["ranked_candidates"][0]["ranking_summary"].lower())


if __name__ == "__main__":
    unittest.main()
