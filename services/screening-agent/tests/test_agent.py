"""
Unit tests for Screening Agent
"""

import unittest
from unittest.mock import patch

from app.agent import ScreeningAgent
from app.shared_memory import SharedMemory
from app.worker import heuristic_screen_candidate, coerce_screening_result, screen_with_skill_assessment


class ScreeningAgentTests(unittest.TestCase):
    """Test cases for ScreeningAgent"""
    
    @patch("app.agent.ScreeningLLM")
    def test_uses_llm_result_when_available(self, llm_cls):
        """Test that agent uses LLM when available"""
        # Mock LLM to return successful result
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

        # Create agent and run screening
        agent = ScreeningAgent(agent_type="screening", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "parsed_resume": {
                    "skills": ["python", "fastapi"],
                    "years_experience": 7
                },
                "job_description": "Need python fastapi sql",
            }
        )

        # Verify LLM was called
        llm.score_candidate.assert_called_once()
        
        # Verify result structure
        self.assertIn("payload", result)
        self.assertIn("confidence", result)
        self.assertIn("explanation", result)
        
        # Verify payload contents
        payload = result["payload"]
        self.assertTrue(payload["meets_threshold"])
        self.assertEqual(payload["decision"], "PASS")
        self.assertEqual(payload["matched_skills"], ["python", "fastapi"])
        self.assertEqual(result["confidence"], 0.92)

    @patch("app.agent.ScreeningLLM")
    def test_falls_back_when_llm_fails(self, llm_cls):
        """Test that agent falls back to heuristic when LLM fails"""
        # Mock LLM to raise exception
        llm = llm_cls.return_value
        llm.score_candidate.side_effect = RuntimeError("llm unavailable")

        # Create agent and run screening
        agent = ScreeningAgent(agent_type="screening", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "parsed_resume": {
                    "skills": ["python"],
                    "years_experience": 5
                },
                "job_description": "Need python sql",
            }
        )

        # Verify result still generated (via fallback)
        self.assertIn("payload", result)
        self.assertIn("qualification_score", result["payload"])
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        
        # Verify heuristic method was used
        details = result["payload"].get("details", {})
        self.assertEqual(details.get("method"), "heuristic")
        self.assertTrue(result["payload"]["needs_human_review"])
        self.assertIn("heuristic", result["explanation"])

    def test_decision_threshold(self):
        """Test that decision correctly reflects threshold"""
        agent = ScreeningAgent(agent_type="screening", shared_memory=SharedMemory())
        
        # Mock LLM to return score above threshold
        with patch.object(agent.llm, 'score_candidate') as mock_llm:
            mock_llm.return_value = {
                "qualification_score": 0.75,
                "meets_threshold": True,
                "matched_skills": ["python", "sql"],
                "missing_skills": [],
                "years_experience": 5,
                "confidence": 0.85,
                "explanation": "Good match"
            }
            
            result = agent.handle({
                "parsed_resume": {"skills": ["python", "sql"], "years_experience": 5},
                "job_description": "python sql required"
            })
            
            self.assertEqual(result["payload"]["decision"], "PASS")
        
        # Mock LLM to return score below threshold
        with patch.object(agent.llm, 'score_candidate') as mock_llm:
            mock_llm.return_value = {
                "qualification_score": 0.45,
                "meets_threshold": False,
                "matched_skills": ["python"],
                "missing_skills": ["sql"],
                "years_experience": 2,
                "confidence": 0.70,
                "explanation": "Insufficient match"
            }
            
            result = agent.handle({
                "parsed_resume": {"skills": ["python"], "years_experience": 2},
                "job_description": "python sql required"
            })
            
            self.assertEqual(result["payload"]["decision"], "FAIL")

    def test_uses_skill_assessment_artifact_when_provided(self):
        agent = ScreeningAgent(agent_type="screening", shared_memory=SharedMemory())

        result = agent.handle(
            {
                "parsed_resume": {"skills": ["python"], "years_experience": 5},
                "job_description": "Need python fastapi sql",
                "job_requirements": {
                    "required_skills": ["python", "fastapi"],
                    "preferred_skills": ["sql"],
                    "min_years_experience": 3,
                },
                "skill_assessment": {
                    "skills_score": 0.7,
                    "matched_required_skills": ["python"],
                    "missing_required_skills": ["fastapi"],
                    "matched_preferred_skills": [],
                    "missing_preferred_skills": ["sql"],
                    "confidence": 0.82,
                },
            }
        )

        self.assertEqual(result["payload"]["details"]["method"], "skill_assessment_supported")
        self.assertEqual(result["payload"]["matched_skills"], ["python"])
        self.assertIn("fastapi", result["payload"]["missing_skills"])
        self.assertTrue(result["payload"]["meets_threshold"])
        self.assertEqual(result["confidence"], 0.82)
        self.assertFalse(result["payload"]["needs_human_review"])


class HeuristicTests(unittest.TestCase):
    """Test cases for heuristic screening fallback"""
    
    def test_perfect_match(self):
        """Test heuristic with perfect skill match"""
        result = heuristic_screen_candidate(
            parsed_resume={
                "skills": ["Python", "SQL", "AWS"],
                "years_experience": 10
            },
            job_description="python sql aws"
        )
        
        self.assertGreater(result["qualification_score"], 0.8)
        self.assertTrue(result["meets_threshold"])
        self.assertIn("python", result["matched_skills"])
        self.assertIn("sql", result["matched_skills"])
        self.assertIn("aws", result["matched_skills"])

    def test_partial_match(self):
        """Test heuristic with partial skill match"""
        result = heuristic_screen_candidate(
            parsed_resume={
                "skills": ["Python"],
                "years_experience": 3
            },
            job_description="python sql aws docker"
        )
        
        self.assertLess(result["qualification_score"], 0.6)
        self.assertFalse(result["meets_threshold"])
        self.assertEqual(len(result["matched_skills"]), 1)
        self.assertGreater(len(result["missing_skills"]), 0)

    def test_structured_requirements(self):
        """Test heuristic with structured job requirements"""
        result = heuristic_screen_candidate(
            parsed_resume={
                "skills": ["Python", "FastAPI"],
                "years_experience": 5
            },
            job_description="Backend developer position",
            job_requirements={
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                "preferred_skills": ["Docker", "AWS"]
            }
        )
        
        self.assertIn("python", result["matched_skills"])
        self.assertIn("fastapi", result["matched_skills"])
        self.assertIn("postgresql", result["missing_skills"])
        self.assertNotIn("backend", result["missing_skills"])

    def test_screen_with_skill_assessment(self):
        result = screen_with_skill_assessment(
            parsed_resume={"years_experience": 4},
            job_requirements={"min_years_experience": 2},
            skill_assessment={
                "skills_score": 0.75,
                "matched_required_skills": ["python", "fastapi"],
                "missing_required_skills": ["sql"],
                "matched_preferred_skills": ["docker"],
                "missing_preferred_skills": [],
                "confidence": 0.88,
            },
        )

        self.assertTrue(result["meets_threshold"])
        self.assertEqual(result["matched_skills"], ["python", "fastapi", "docker"])
        self.assertIn("sql", result["missing_skills"])


class CoerceResultTests(unittest.TestCase):
    """Test cases for result coercion/normalization"""
    
    def test_valid_result(self):
        """Test coercing a valid result"""
        input_result = {
            "qualification_score": 0.85,
            "meets_threshold": True,
            "matched_skills": ["python", "sql"],
            "missing_skills": ["aws"],
            "years_experience": 7,
            "confidence": 0.90,
            "explanation": "Strong match"
        }
        
        output = coerce_screening_result(input_result)
        
        self.assertEqual(output["qualification_score"], 0.85)
        self.assertTrue(output["meets_threshold"])
        self.assertEqual(output["years_experience"], 7)
        self.assertEqual(output["confidence"], 0.90)

    def test_missing_fields(self):
        """Test coercing result with missing fields"""
        input_result = {
            "qualification_score": 0.75
            # Missing other fields
        }
        
        output = coerce_screening_result(input_result)
        
        # Should provide defaults
        self.assertEqual(output["qualification_score"], 0.75)
        self.assertIsInstance(output["matched_skills"], list)
        self.assertIsInstance(output["missing_skills"], list)
        self.assertIsInstance(output["years_experience"], int)
        self.assertIsInstance(output["confidence"], float)

    def test_invalid_types(self):
        """Test coercing result with invalid types"""
        input_result = {
            "qualification_score": "not a number",
            "matched_skills": "not a list",
            "years_experience": "five",
            "confidence": 2.5  # Out of range
        }
        
        output = coerce_screening_result(input_result)
        
        # Should handle gracefully
        self.assertEqual(output["qualification_score"], 0.0)
        self.assertEqual(output["matched_skills"], [])
        self.assertEqual(output["years_experience"], 0)
        self.assertEqual(output["confidence"], 1.0)  # Clamped to max


if __name__ == "__main__":
    unittest.main()
