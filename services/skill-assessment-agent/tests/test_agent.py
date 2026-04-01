import unittest
from unittest.mock import patch

from app.agent import SkillAssessmentAgent
from app.shared_memory import SharedMemory
from app.worker import coerce_skill_assessment_result, heuristic_assess_skills


class SkillAssessmentAgentTests(unittest.TestCase):
    @patch("app.agent.SkillAssessmentLLM")
    def test_uses_llm_result_when_available(self, llm_cls):
        llm = llm_cls.return_value
        llm.assess_skills.return_value = {
            "skills_score": 0.84,
            "matched_required_skills": ["python", "fastapi"],
            "matched_preferred_skills": ["docker"],
            "missing_required_skills": ["sql"],
            "missing_preferred_skills": [],
            "detected_soft_skills": ["communication"],
            "matched_soft_skills": ["communication"],
            "missing_soft_skills": [],
            "strengths": ["python", "fastapi", "communication"],
            "gaps": ["sql"],
            "gap_analysis": "Strong backend alignment with one database gap.",
            "confidence": 0.9,
        }

        agent = SkillAssessmentAgent(agent_type="skill_assessment", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "parsed_resume": {"skills": ["python", "fastapi"], "summary": "Strong communicator"},
                "resume_text": "Python FastAPI engineer with strong communication skills",
                "job_description": "Need python fastapi sql and communication",
                "job_requirements": {
                    "required_skills": ["python", "fastapi", "sql"],
                    "preferred_skills": ["docker"],
                },
            }
        )

        self.assertEqual(result["payload"]["skills_score"], 0.84)
        self.assertEqual(result["confidence"], 0.9)
        self.assertIn("Matched required skills", result["explanation"])

    @patch("app.agent.SkillAssessmentLLM")
    def test_falls_back_when_llm_fails(self, llm_cls):
        llm_cls.return_value.assess_skills.side_effect = RuntimeError("llm unavailable")

        agent = SkillAssessmentAgent(agent_type="skill_assessment", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "parsed_resume": {"skills": ["python"], "summary": "Worked across teams"},
                "resume_text": "Python backend engineer who collaborated with cross-functional teams",
                "job_description": "Need python sql and collaboration",
                "job_requirements": {"required_skills": ["python", "sql"]},
            }
        )

        self.assertIn("payload", result)
        self.assertEqual(result["payload"]["details"]["method"], "heuristic")
        self.assertGreaterEqual(result["payload"]["skills_score"], 0.0)
        self.assertIn("heuristic", result["explanation"])


class SkillAssessmentWorkerTests(unittest.TestCase):
    def test_heuristic_detects_gaps_and_soft_skills(self):
        result = heuristic_assess_skills(
            parsed_resume={
                "skills": ["Python", "FastAPI"],
                "summary": "Collaborative backend engineer with strong communication",
            },
            resume_text="Built Python APIs and worked cross-functional with product and design",
            job_description="Need python sql docker and communication in a collaborative team",
            job_requirements={
                "required_skills": ["python", "sql"],
                "preferred_skills": ["docker"],
            },
        )

        self.assertIn("python", result["matched_required_skills"])
        self.assertIn("sql", result["missing_required_skills"])
        self.assertIn("communication", result["detected_soft_skills"])
        self.assertGreater(result["skills_score"], 0.0)

    def test_coerce_skill_assessment_result_handles_invalid_types(self):
        output = coerce_skill_assessment_result(
            {
                "skills_score": "0.9",
                "matched_required_skills": "python",
                "missing_required_skills": ["sql"],
                "detected_soft_skills": ["communication"],
                "gap_analysis": "",
                "confidence": "1.5",
            }
        )

        self.assertEqual(output["skills_score"], 0.9)
        self.assertEqual(output["matched_required_skills"], [])
        self.assertEqual(output["missing_required_skills"], ["sql"])
        self.assertEqual(output["confidence"], 1.0)
        self.assertIn("Skill assessment completed", output["gap_analysis"])


if __name__ == "__main__":
    unittest.main()
