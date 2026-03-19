import json
import re
from typing import Any

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SEC


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return json.loads(stripped)


class ScreeningLLM:
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY)
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC) if self.enabled else None

    def score_candidate(self, *, parsed_resume: dict[str, Any], job_description: str) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = self._client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are a qualification screening agent. Score a candidate against a job description. "
                "Return strict JSON only with keys: qualification_score, meets_threshold, matched_skills, "
                "missing_skills, years_experience, confidence, explanation. qualification_score and confidence "
                "must be numbers from 0 to 1. matched_skills and missing_skills must be arrays of lowercase strings."
            ),
            input=(
                f"Job description:\n{job_description}\n\n"
                f"Parsed resume:\n{json.dumps(parsed_resume)}"
            ),
        )
        return _extract_json(response.output_text)
