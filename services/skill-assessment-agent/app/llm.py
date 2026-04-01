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


class SkillAssessmentLLM:
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY)
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC) if self.enabled else None

    def assess_skills(
        self,
        *,
        parsed_resume: dict[str, Any],
        resume_text: str,
        job_description: str,
        job_requirements: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        requirements = job_requirements or {}
        response = self._client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are a skill assessment agent for a hiring system. "
                "Assess candidate competencies against a job and return strict JSON only. "
                "You must evaluate only stated technical and soft-skill evidence from the resume. "
                "Do not infer protected attributes or culture fit. "
                "Return exactly these keys: "
                "skills_score, matched_required_skills, matched_preferred_skills, "
                "missing_required_skills, missing_preferred_skills, detected_soft_skills, "
                "matched_soft_skills, missing_soft_skills, strengths, gaps, gap_analysis, confidence. "
                "All skill arrays must contain lowercase strings. skills_score and confidence must be numbers from 0 to 1."
            ),
            input=(
                f"Job description:\n{job_description}\n\n"
                f"Structured requirements:\n{json.dumps(requirements)}\n\n"
                f"Parsed resume:\n{json.dumps(parsed_resume)}\n\n"
                f"Resume text:\n{resume_text}"
            ),
        )
        return _extract_json(response.output_text)
