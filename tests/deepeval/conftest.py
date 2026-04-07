"""
DeepEval test configuration and shared fixtures.

Uses OpenAI gpt-4o-mini as the LLM judge model for evaluation metrics.
Golden datasets are loaded from JSON files in the golden_datasets/ directory.
"""

import json
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GOLDEN_DIR = Path(__file__).parent / "golden_datasets"
CACHED_DIR = Path(__file__).parent / "cached_responses"

# ---------------------------------------------------------------------------
# Lenient thresholds (Phase 5 cold-start; tighten over time)
# ---------------------------------------------------------------------------
HALLUCINATION_THRESHOLD = 0.5
RELEVANCY_THRESHOLD = 0.5
BIAS_THRESHOLD = 0.5
TOXICITY_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# DeepEval model configuration
# ---------------------------------------------------------------------------
DEEPEVAL_MODEL = os.getenv("DEEPEVAL_MODEL", "gpt-4o-mini")


def _load_golden(filename: str) -> list[dict]:
    """Load a golden dataset JSON file."""
    path = GOLDEN_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def intake_cases():
    return _load_golden("intake_cases.json")


@pytest.fixture(scope="session")
def screening_cases():
    return _load_golden("screening_cases.json")


@pytest.fixture(scope="session")
def skill_assessment_cases():
    return _load_golden("skill_assessment_cases.json")


@pytest.fixture(scope="session")
def audit_cases():
    return _load_golden("audit_cases.json")


@pytest.fixture(scope="session")
def ranking_cases():
    return _load_golden("ranking_cases.json")
