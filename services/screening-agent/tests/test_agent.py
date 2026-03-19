import unittest
from unittest.mock import patch

from app.agent import ScreeningAgent
from app.shared_memory import SharedMemory


class ScreeningAgentTests(unittest.TestCase):
    @patch("app.agent.ScreeningLLM")
    def test_uses_llm_result_when_available(self, llm_cls):
        llm = llm_cls.return_value
        llm.score_candidate.return_value = {
            "qualification_score": 0.88,
            "meets_threshold": True,
            "matched_skills": ["python", "fastapi"],
            "missing_skills": ["sql"],
            "years_experience": 7,
            "confidence": 0.92,
            "explanation": "Strong backend match",
        }

        agent = ScreeningAgent(agent_type="screening", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "parsed_resume": {"skills": ["python", "fastapi"], "years_experience": 7},
                "job_description": "Need python fastapi sql",
            }
        )

        self.assertTrue(result["payload"]["meets_threshold"])
        self.assertEqual(result["payload"]["matched_skills"], ["python", "fastapi"])
        self.assertEqual(result["confidence"], 0.92)

    @patch("app.agent.ScreeningLLM")
    def test_falls_back_when_llm_fails(self, llm_cls):
        llm = llm_cls.return_value
        llm.score_candidate.side_effect = RuntimeError("llm unavailable")

        agent = ScreeningAgent(agent_type="screening", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "parsed_resume": {"skills": ["python"], "years_experience": 5},
                "job_description": "Need python sql",
            }
        )

        self.assertIn("qualification_score", result["payload"])
        self.assertGreaterEqual(result["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
