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

    def test_falls_back_to_weighted_scores(self):
        result = heuristic_rank_candidates(
            candidates=[
                {"id": "c-1", "scores": {"qualification": 0.7, "skills": 0.5}},
            ]
        )

        self.assertAlmostEqual(result["ranked_candidates"][0]["score"], 0.64)


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
        self.assertEqual(result["payload"]["details"]["method"], "heuristic_composite_score")


if __name__ == "__main__":
    unittest.main()
