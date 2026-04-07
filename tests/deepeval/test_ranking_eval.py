"""
DeepEval tests for the Ranking Agent.

Evaluates:
- Fairness: ranking order must be consistent with scores
- Human review impact: flagged candidates should be held for review
- Deterministic: ranking agent is heuristic-based, so tests are deterministic

Note: The ranking agent does NOT use an LLM. Tests here validate the
heuristic logic directly against expected golden outputs.
"""

import sys
from pathlib import Path

import pytest

# Add the ranking agent to the path so we can import its worker
RANKING_AGENT_PATH = (
    Path(__file__).parent.parent.parent / "services" / "ranking-agent"
)
sys.path.insert(0, str(RANKING_AGENT_PATH))

from app.worker import heuristic_rank_candidates  # noqa: E402


class TestRankingOrder:
    """Verify ranking produces correct order based on scores."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, ranking_cases):
        self.cases = ranking_cases

    def _find_case(self, case_id: str) -> dict:
        return next(c for c in self.cases if c["id"] == case_id)

    def test_clear_ranking_order(self):
        """Candidates with clearly different scores must be ranked correctly."""
        case = self._find_case("rank-001")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        ranked = result["ranked_candidates"]
        actual_order = [c["candidate_id"] for c in ranked]
        expected_order = case["expected_output"]["rank_order"]

        assert actual_order == expected_order, (
            f"Expected order {expected_order}, got {actual_order}"
        )

    def test_top_candidate(self):
        """Top candidate should match expected top."""
        case = self._find_case("rank-001")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        assert result["top_candidate_id"] == case["expected_output"]["top_candidate_id"]

    def test_top_action_is_invite(self):
        """Top scoring candidate should be recommended for interview."""
        case = self._find_case("rank-001")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        top = result["ranked_candidates"][0]
        assert top["recommended_action"] == case["expected_output"]["top_action"]

    def test_bottom_action_is_reject(self):
        """Lowest scoring candidate should be rejected."""
        case = self._find_case("rank-001")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        bottom = result["ranked_candidates"][-1]
        assert bottom["recommended_action"] == case["expected_output"]["bottom_action"]


class TestRankingTieBreaking:
    """Verify tie-breaking behavior for candidates with similar scores."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, ranking_cases):
        self.cases = ranking_cases

    def _find_case(self, case_id: str) -> dict:
        return next(c for c in self.cases if c["id"] == case_id)

    def test_similar_score_candidates_both_scored(self):
        """Both candidates must receive a ranking score."""
        case = self._find_case("rank-002")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        ranked = result["ranked_candidates"]
        assert len(ranked) == 2
        assert all(c["score"] > 0 for c in ranked)

    def test_similar_scores_within_delta(self):
        """Candidates with similar inputs should have scores within acceptable delta."""
        case = self._find_case("rank-002")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        ranked = result["ranked_candidates"]
        delta = abs(ranked[0]["score"] - ranked[1]["score"])
        max_delta = case["expected_output"]["scores_within_delta"]
        assert delta <= max_delta, (
            f"Score delta {delta} exceeds acceptable max {max_delta}"
        )


class TestRankingHumanReview:
    """Verify human review flags affect ranking actions correctly."""

    @pytest.fixture(autouse=True)
    def _load_cases(self, ranking_cases):
        self.cases = ranking_cases

    def _find_case(self, case_id: str) -> dict:
        return next(c for c in self.cases if c["id"] == case_id)

    def test_flagged_candidate_held(self):
        """Candidate with needs_human_review=true should be held for review."""
        case = self._find_case("rank-003")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        flagged = next(
            c for c in result["ranked_candidates"] if c["candidate_id"] == "c1"
        )
        assert flagged["recommended_action"] == case["expected_output"]["flagged_candidate_action"]

    def test_clean_candidate_not_held(self):
        """Candidate without human review flag should not be held."""
        case = self._find_case("rank-003")
        result = heuristic_rank_candidates(candidates=case["input"]["candidates"])

        clean = next(
            c for c in result["ranked_candidates"] if c["candidate_id"] == "c2"
        )
        assert clean["recommended_action"] != "HOLD_FOR_REVIEW"
