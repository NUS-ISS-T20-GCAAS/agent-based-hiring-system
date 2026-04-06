import json
import re
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - depends on runtime environment
    OpenAI = None

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SEC


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return json.loads(stripped)


class CoordinatorLLM:
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY and OpenAI is not None)
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC) if self.enabled else None

    def plan_workflow(
        self,
        *,
        job_id: str,
        job_description: str,
        resume_url: str,
        resume_text: str,
        job_requirements: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY or OpenAI SDK is not configured test")

        response = self._client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are the coordinator agent for a hiring workflow. "
                "Create a concise orchestration plan that helps downstream agents focus on the right evidence. "
                "Return strict JSON only with exactly these keys: "
                "priority_skills, screening_focus, audit_focus, risk_flags, orchestration_notes, confidence. "
                "All list values must be arrays of short lowercase strings. "
                "confidence must be a number from 0 to 1. "
                "Focus on technical requirements, missing information, ambiguity, and workflow risks. "
                "Do not infer protected attributes or culture fit."
            ),
            input=json.dumps(
                {
                    "job_id": job_id,
                    "job_description": job_description,
                    "resume_url": resume_url,
                    "resume_text": resume_text,
                    "job_requirements": job_requirements,
                }
            ),
        )
        return _extract_json(response.output_text)
