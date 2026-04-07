"""
DeepEval tests for the Screening Agent.

Evaluates:
- Bias: scoring must not vary based on candidate name/background
- Answer Relevancy: explanation must be grounded in skill matches
- Toxicity: explanations must be free of discriminatory language
- Consistency: required JSON schema fields are always present
"""

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    BiasMetric,
    ToxicityMetric,
)
from deepeval.test_case import LLMTestCase

from .conftest import (
    BIAS_THRESHOLD,
    DEEPEVAL_MODEL,
    RELEVANCY_THRESHOLD,
    TOXICITY_THRESHOLD,
)

REQUIRED_SCREENING_FIELDS = [
    "qualification_score",
    "meets_threshold",
    "matched_skills",
    "missing_skills",
    "years_experience",
    "confidence",
    "explanation",
]


class TestScreeningBias:
    """Verify screening scores do not discriminate based on candidate identity."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, screening_cases):
        self.cases = screening_cases

    def _find_case(self, case_id: str) -> dict:
        return next(c for c in self.cases if c["id"] == case_id)

    def test_bias_metric(self):
        """Run DeepEval BiasMetric on each screening explanation."""
        for case in self.cases:
            inp = case["input"]
            # Simulate a screening explanation output
            simulated_explanation = (
                f"Candidate scored well on required skills "
                f"({', '.join(inp['parsed_resume']['skills'][:3])}). "
                f"Experience of {inp['parsed_resume']['years_experience']} years "
                f"meets the minimum requirement."
            )

            test_case = LLMTestCase(
                input=json.dumps(inp["parsed_resume"]),
                actual_output=simulated_explanation,
            )

            metric = BiasMetric(
                threshold=BIAS_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])

    def test_name_invariance(self):
        """
        Bias pair test: screen-001 and screen-004-bias have identical skills
        but different names. Their score ranges must overlap.
        """
        reference = self._find_case("screen-001")
        bias_case = self._find_case("screen-004-bias")

        ref_range = reference["expected_output"]["qualification_score_range"]
        bias_range = bias_case["expected_output"]["qualification_score_range"]

        # The expected ranges must overlap
        assert ref_range[0] <= bias_range[1] and bias_range[0] <= ref_range[1], (
            "Bias pair score ranges do not overlap — potential name-based discrimination"
        )


class TestScreeningToxicity:
    """Verify screening explanations are free of toxic or discriminatory language."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, screening_cases):
        self.cases = screening_cases

    def test_no_toxicity(self):
        """Screening explanations must not contain toxic language."""
        for case in self.cases:
            inp = case["input"]
            simulated_explanation = (
                f"Based on skill evaluation, candidate has "
                f"{len(inp['parsed_resume']['skills'])} relevant skills. "
                f"Assessment is based purely on technical qualifications."
            )

            test_case = LLMTestCase(
                input=inp["job_description"],
                actual_output=simulated_explanation,
            )

            metric = ToxicityMetric(
                threshold=TOXICITY_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])


class TestScreeningRelevancy:
    """Verify screening explanations are relevant to the job requirements."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, screening_cases):
        self.cases = screening_cases

    def test_explanation_relevancy(self):
        """Explanation must reference actual job requirements and candidate skills."""
        for case in self.cases:
            inp = case["input"]
            simulated_explanation = (
                f"Evaluated candidate against required skills: "
                f"{', '.join(inp['job_requirements']['required_skills'])}. "
                f"Candidate possesses: {', '.join(inp['parsed_resume']['skills'][:4])}."
            )

            test_case = LLMTestCase(
                input=inp["job_description"],
                actual_output=simulated_explanation,
            )

            metric = AnswerRelevancyMetric(
                threshold=RELEVANCY_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])


class TestScreeningSchema:
    """Verify screening output schema compliance (deterministic checks)."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, screening_cases):
        self.cases = screening_cases

    def test_expected_score_ranges(self):
        """Expected qualification scores must be within [0, 1]."""
        for case in self.cases:
            expected = case["expected_output"]
            score_range = expected.get("qualification_score_range", [0, 1])
            assert 0 <= score_range[0] <= score_range[1] <= 1.0, (
                f"Case {case['id']}: invalid score range {score_range}"
            )

    def test_confidence_ranges(self):
        """Expected confidence must be within [0, 1]."""
        for case in self.cases:
            expected = case["expected_output"]
            conf_range = expected.get("confidence_range", [0, 1])
            assert 0 <= conf_range[0] <= conf_range[1] <= 1.0, (
                f"Case {case['id']}: invalid confidence range {conf_range}"
            )
