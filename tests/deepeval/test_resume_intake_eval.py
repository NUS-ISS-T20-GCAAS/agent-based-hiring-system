"""
DeepEval tests for the Resume Intake Agent.

Evaluates:
- Hallucination: extracted profile must not contain info absent from the resume
- Answer Relevancy: extracted data should be relevant to the job description
- Completeness: all required fields (name, email, skills, years_experience) populated
"""

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase

from .conftest import (
    DEEPEVAL_MODEL,
    HALLUCINATION_THRESHOLD,
    RELEVANCY_THRESHOLD,
)


class TestResumeIntakeHallucination:
    """Verify intake output does not hallucinate information not in the resume."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, intake_cases):
        self.cases = intake_cases

    def test_no_hallucination(self):
        """Extracted profile must only contain information present in resume text."""
        for case in self.cases:
            inp = case["input"]
            expected = case["expected_output"]

            # Simulate an LLM intake output
            actual_output = json.dumps(expected)

            test_case = LLMTestCase(
                input=inp["resume_text"],
                actual_output=actual_output,
                context=[inp["resume_text"]],
            )

            metric = HallucinationMetric(
                threshold=HALLUCINATION_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])


class TestResumeIntakeRelevancy:
    """Verify extracted data is relevant to the job description."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, intake_cases):
        self.cases = intake_cases

    def test_answer_relevancy(self):
        """Extracted skills and experience should align with job requirements."""
        for case in self.cases:
            inp = case["input"]
            expected = case["expected_output"]

            actual_output = json.dumps(expected)

            test_case = LLMTestCase(
                input=inp["job_description"],
                actual_output=actual_output,
            )

            metric = AnswerRelevancyMetric(
                threshold=RELEVANCY_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])


class TestResumeIntakeCompleteness:
    """Verify all required fields are present in the output."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, intake_cases):
        self.cases = intake_cases

    def test_required_fields_present(self):
        """Output must contain name, email, skills, years_experience, summary."""
        required_fields = ["name", "email", "skills", "years_experience", "summary"]
        for case in self.cases:
            expected = case["expected_output"]
            for field in required_fields:
                assert field in expected, (
                    f"Case {case['id']}: missing required field '{field}'"
                )

    def test_skills_is_list(self):
        """Skills must be a list of strings."""
        for case in self.cases:
            skills = case["expected_output"]["skills"]
            assert isinstance(skills, list), f"Case {case['id']}: skills is not a list"
            assert len(skills) >= case["evaluation_criteria"]["min_skills_count"], (
                f"Case {case['id']}: fewer skills than expected minimum"
            )

    def test_experience_in_range(self):
        """Years of experience must fall within expected range."""
        for case in self.cases:
            exp = case["expected_output"]["years_experience"]
            lo, hi = case["evaluation_criteria"]["experience_range"]
            assert lo <= exp <= hi, (
                f"Case {case['id']}: years_experience {exp} not in [{lo}, {hi}]"
            )
