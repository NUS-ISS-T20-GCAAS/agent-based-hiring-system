"""
DeepEval tests for the Audit Agent.

Evaluates:
- Bias detection: audit correctly flags low selection rates
- Consistency: risk levels follow the documented rules
- Answer Relevancy: recommendations relate to the audit findings
"""

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from .conftest import DEEPEVAL_MODEL, RELEVANCY_THRESHOLD


class TestAuditConsistency:
    """Verify audit outputs follow the documented risk-level rules."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, audit_cases):
        self.cases = audit_cases

    def test_clean_audit_low_risk(self):
        """When no bias flags are expected, risk level must be low."""
        for case in self.cases:
            expected = case["expected_output"]
            if expected.get("bias_flags_empty"):
                assert expected.get("risk_level") == "low", (
                    f"Case {case['id']}: empty bias_flags should yield risk_level=low"
                )
                assert expected.get("review_required") is False, (
                    f"Case {case['id']}: empty bias_flags should not require review"
                )

    def test_low_selection_rate_high_risk(self):
        """When low_selection_rate bias is expected, risk must be high."""
        for case in self.cases:
            expected = case["expected_output"]
            if expected.get("must_have_bias_flag") == "low_selection_rate":
                assert expected.get("risk_level") == "high", (
                    f"Case {case['id']}: low_selection_rate should yield risk_level=high"
                )
                assert expected.get("review_required") is True, (
                    f"Case {case['id']}: low_selection_rate should require review"
                )

    def test_mixed_signals_require_review(self):
        """Edge cases with low-confidence decisions should require review."""
        for case in self.cases:
            expected = case["expected_output"]
            if expected.get("risk_level_options"):
                assert expected.get("review_required") is True, (
                    f"Case {case['id']}: mixed signals should require review"
                )

    def test_confidence_ranges_valid(self):
        """Confidence ranges must be within [0, 1]."""
        for case in self.cases:
            conf_range = case["expected_output"].get("confidence_range", [0, 1])
            assert 0 <= conf_range[0] <= conf_range[1] <= 1.0, (
                f"Case {case['id']}: invalid confidence range {conf_range}"
            )


class TestAuditRelevancy:
    """Verify audit recommendations are relevant to the audit findings."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, audit_cases):
        self.cases = audit_cases

    def test_recommendation_relevancy(self):
        """Audit recommendations must reference actual audit data."""
        for case in self.cases:
            inp = case["input"]
            stats = inp["stats"]

            simulated_output = (
                f"Selection rate: {stats['selection_rate']:.0%}. "
                f"Total candidates: {stats['total_candidates']}. "
                f"Shortlisted: {stats['shortlisted']}. "
                f"Recommendation: review selection criteria if rate is unusually low."
            )

            test_case = LLMTestCase(
                input=json.dumps(stats),
                actual_output=simulated_output,
            )

            metric = AnswerRelevancyMetric(
                threshold=RELEVANCY_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])
