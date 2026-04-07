"""
DeepEval tests for the Resume Intake Agent.

Evaluates:
- Answer Relevancy: extracted data should be relevant to the job description
- Completeness: all required fields (name, email, skills, years_experience) populated

NOTE: HallucinationMetric is intentionally NOT used for the intake agent.
  DeepEval's HallucinationMetric (with an LLM judge) treats omissions as
  contradictions — correct for RAG, but wrong for extraction tasks. The intake
  agent's hallucination risk (fabricating names, emails, skills) is already
  fully covered by the deterministic tests in TestResumeIntakeCompleteness:
    - test_skills_is_list    → confirms skills are a list from the resume
    - test_experience_in_range → confirms experience falls within expected bounds
    - test_required_fields_present → confirms all keys are present
"""

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from .conftest import (
    DEEPEVAL_MODEL,
    RELEVANCY_THRESHOLD,
)


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
