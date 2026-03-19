import unittest
from unittest.mock import patch

from app.agent import ResumeIntakeAgent
from app.shared_memory import SharedMemory


class ResumeIntakeAgentTests(unittest.TestCase):
    @patch("app.agent.ResumeIntakeLLM")
    def test_uses_llm_result_when_available(self, llm_cls):
        llm = llm_cls.return_value
        llm.parse_resume.return_value = {
            "name": "Alice",
            "email": "alice@example.com",
            "skills": ["Python", "FastAPI"],
            "years_experience": 6,
            "summary": "Backend engineer",
        }

        agent = ResumeIntakeAgent(agent_type="resume_intake", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "resume_text": "Alice has 6 years of Python and FastAPI experience",
                "resume_url": "upload://alice.txt",
                "job_description": "Need python fastapi",
            }
        )

        self.assertEqual(result["payload"]["name"], "Alice")
        self.assertEqual(result["payload"]["skills"], ["python", "fastapi"])
        self.assertGreaterEqual(result["confidence"], 0.9)

    @patch("app.agent.ResumeIntakeLLM")
    def test_falls_back_when_llm_fails(self, llm_cls):
        llm = llm_cls.return_value
        llm.parse_resume.side_effect = RuntimeError("llm unavailable")

        agent = ResumeIntakeAgent(agent_type="resume_intake", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "resume_text": "Bob 5 years python bob@example.com",
                "resume_url": "upload://bob.txt",
                "job_description": "Need python",
            }
        )

        self.assertEqual(result["payload"]["email"], "bob@example.com")
        self.assertEqual(result["payload"]["skills"], ["python"])
        self.assertLess(result["confidence"], 0.9)


if __name__ == "__main__":
    unittest.main()
