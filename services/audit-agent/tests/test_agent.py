import unittest
from unittest.mock import patch

from app.agent import AuditAgent
from app.shared_memory import SharedMemory
from app.worker import coerce_audit_result, heuristic_audit_check, normalize_audit_result


class AuditAgentTests(unittest.TestCase):
    @patch("app.agent.AuditLLM")
    def test_uses_llm_result_when_available(self, llm_cls):
        llm = llm_cls.return_value
        llm.audit.return_value = {
            "job_id": "job-1",
            "selection_rate": 0.35,
            "total_candidates": 20,
            "shortlisted": 7,
            "bias_flags": ["small_sample_size"],
            "risk_level": "medium",
            "review_required": True,
            "recommendations": ["Review thresholds"],
            "data_completeness": 0.9,
            "confidence": 0.88,
        }

        agent = AuditAgent(agent_type="audit", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "job_id": "job-1",
                "stats": {"total_candidates": 20, "shortlisted": 7},
            }
        )

        llm.audit.assert_called_once()
        self.assertEqual(result["payload"]["risk_level"], "low")
        self.assertFalse(result["payload"]["review_required"])
        self.assertEqual(result["payload"]["bias_flags"], [])
        self.assertEqual(result["confidence"], 0.88)

    @patch("app.agent.AuditLLM")
    def test_falls_back_when_llm_fails(self, llm_cls):
        llm = llm_cls.return_value
        llm.audit.side_effect = RuntimeError("llm unavailable")

        agent = AuditAgent(agent_type="audit", shared_memory=SharedMemory())
        result = agent.handle(
            {
                "job_id": "job-1",
                "stats": {"total_candidates": 2, "shortlisted": 0},
            }
        )

        details = result["payload"].get("details", {})
        self.assertEqual(details.get("method"), "heuristic")
        self.assertTrue(result["payload"]["review_required"])
        self.assertIn("Manual audit review is required.", result["explanation"])


class AuditWorkerTests(unittest.TestCase):
    def test_heuristic_flags_small_sample(self):
        result = heuristic_audit_check(
            job_id="job-1",
            stats={"total_candidates": 2, "shortlisted": 1},
            candidates=[],
            decisions=[],
        )
        self.assertIn("small_sample_size", result["bias_flags"])
        self.assertTrue(result["review_required"])

    def test_heuristic_flags_low_selection_rate(self):
        result = heuristic_audit_check(
            job_id="job-2",
            stats={"total_candidates": 10, "shortlisted": 1},
            candidates=[],
            decisions=[],
        )
        self.assertIn("low_selection_rate", result["bias_flags"])
        self.assertEqual(result["risk_level"], "high")

    def test_coerces_result(self):
        output = coerce_audit_result(
            {
                "job_id": "job-3",
                "selection_rate": "0.25",
                "total_candidates": "8",
                "shortlisted": "2",
                "bias_flags": ["small_sample_size"],
                "risk_level": "MEDIUM",
                "review_required": 1,
                "recommendations": ["Review shortlist threshold"],
                "data_completeness": "0.8",
                "confidence": "0.7",
            }
        )
        self.assertEqual(output["job_id"], "job-3")
        self.assertEqual(output["risk_level"], "medium")
        self.assertTrue(output["review_required"])
        self.assertEqual(output["shortlisted"], 2)

    def test_normalize_audit_result_enforces_no_flag_invariants(self):
        output = normalize_audit_result(
            result={
                "job_id": "job-4",
                "selection_rate": 0.2,
                "total_candidates": 8,
                "shortlisted": 2,
                "bias_flags": [],
                "risk_level": "high",
                "review_required": True,
                "recommendations": ["Investigate"],
                "data_completeness": 0.0,
                "confidence": 0.83,
            },
            job_id="job-4",
            stats={"total_candidates": 8, "shortlisted": 8},
            candidates=[{"status": "shortlisted"} for _ in range(8)],
            decisions=[{"decision_type": "resume_intake_result"} for _ in range(8)],
        )

        self.assertEqual(output["selection_rate"], 1.0)
        self.assertEqual(output["risk_level"], "low")
        self.assertFalse(output["review_required"])
        self.assertEqual(output["bias_flags"], [])
        self.assertEqual(output["data_completeness"], 1.0)
        self.assertEqual(
            output["recommendations"],
            ["No immediate audit action required; continue monitoring outcomes."],
        )

    def test_normalize_audit_result_uses_observed_flags_over_llm_flags(self):
        output = normalize_audit_result(
            result={
                "job_id": "job-5",
                "selection_rate": 0.9,
                "total_candidates": 10,
                "shortlisted": 9,
                "bias_flags": ["small sample size"],
                "risk_level": "low",
                "review_required": False,
                "recommendations": [],
                "data_completeness": 0.4,
                "confidence": 0.71,
            },
            job_id="job-5",
            stats={"total_candidates": 10, "shortlisted": 1},
            candidates=[{"status": "rejected"} for _ in range(9)] + [{"status": "shortlisted"}],
            decisions=[{"decision_type": "resume_intake_result"} for _ in range(10)],
        )

        self.assertEqual(output["bias_flags"], ["low_selection_rate"])
        self.assertEqual(output["risk_level"], "high")
        self.assertTrue(output["review_required"])

    def test_heuristic_uses_artifact_type_when_present(self):
        result = heuristic_audit_check(
            job_id="job-6",
            stats={"total_candidates": 5, "shortlisted": 5},
            candidates=[{"status": "shortlisted"} for _ in range(5)],
            decisions=[{"artifact_type": "resume_intake_result"} for _ in range(5)],
        )

        self.assertEqual(result["bias_flags"], [])
        self.assertFalse(result["review_required"])


if __name__ == "__main__":
    unittest.main()
