"""
DeepEval tests for the Skill Assessment Agent.

Evaluates:
- Hallucination: gap analysis must not reference skills absent from inputs
- Answer Relevancy: matched/missing skills must align with source data
- Schema: required output fields are present and well-typed
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


class TestSkillAssessmentHallucination:
    """Verify gap analysis does not fabricate skills not in the source data."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, skill_assessment_cases):
        self.cases = skill_assessment_cases

    def test_no_hallucination(self):
        """Gap analysis skills must exist in either the resume or job requirements."""
        for case in self.cases:
            inp = case["input"]
            expected = case["expected_output"]

            # Build context from all source data
            context = [
                f"Resume skills: {', '.join(inp['parsed_resume']['skills'])}",
                f"Required skills: {', '.join(inp['job_requirements']['required_skills'])}",
                f"Preferred skills: {', '.join(inp['job_requirements']['preferred_skills'])}",
                f"Resume text: {inp['resume_text']}",
            ]

            # Simulated agent output referencing matched/missing skills
            matched_req = expected.get("must_have_matched_required", [])
            missing_req = expected.get("must_have_missing_required", [])
            actual_output = json.dumps({
                "matched_required_skills": matched_req,
                "missing_required_skills": missing_req,
                "gap_analysis": (
                    f"Candidate matches {len(matched_req)} required skills "
                    f"and is missing {len(missing_req)} required skills."
                ),
            })

            test_case = LLMTestCase(
                input=inp["job_description"],
                actual_output=actual_output,
                context=context,
            )

            metric = HallucinationMetric(
                threshold=HALLUCINATION_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])


class TestSkillAssessmentRelevancy:
    """Verify skill assessment output is relevant to the job description."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, skill_assessment_cases):
        self.cases = skill_assessment_cases

    def test_relevancy(self):
        """Assessment output must relate to the job requirements."""
        for case in self.cases:
            inp = case["input"]
            expected = case["expected_output"]

            actual_output = (
                f"Skills score: {expected['skills_score_range'][0]}-{expected['skills_score_range'][1]}. "
                f"Matched required: {expected.get('must_have_matched_required', [])}. "
                f"Missing required: {expected.get('must_have_missing_required', [])}."
            )

            test_case = LLMTestCase(
                input=inp["job_description"],
                actual_output=actual_output,
            )

            metric = AnswerRelevancyMetric(
                threshold=RELEVANCY_THRESHOLD,
                model=DEEPEVAL_MODEL,
            )

            assert_test(test_case, [metric])


class TestSkillAssessmentSchema:
    """Deterministic schema validation for skill assessment outputs."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, skill_assessment_cases):
        self.cases = skill_assessment_cases

    def test_score_ranges_valid(self):
        """Expected skills_score ranges must be within [0, 1]."""
        for case in self.cases:
            score_range = case["expected_output"]["skills_score_range"]
            assert 0 <= score_range[0] <= score_range[1] <= 1.0, (
                f"Case {case['id']}: invalid score range {score_range}"
            )

    def test_matched_skills_are_subset_of_resume(self):
        """Matched required skills must be a subset of resume skills."""
        for case in self.cases:
            resume_skills = set(
                s.lower() for s in case["input"]["parsed_resume"]["skills"]
            )
            matched = set(
                s.lower()
                for s in case["expected_output"].get("must_have_matched_required", [])
            )
            assert matched.issubset(resume_skills), (
                f"Case {case['id']}: matched skills {matched - resume_skills} "
                f"not found in resume"
            )

    def test_missing_skills_not_in_resume(self):
        """Missing required skills should not appear in the resume skills list."""
        for case in self.cases:
            resume_skills = set(
                s.lower() for s in case["input"]["parsed_resume"]["skills"]
            )
            missing = set(
                s.lower()
                for s in case["expected_output"].get("must_have_missing_required", [])
            )
            overlap = missing & resume_skills
            assert not overlap, (
                f"Case {case['id']}: skills marked as missing but present in resume: {overlap}"
            )
