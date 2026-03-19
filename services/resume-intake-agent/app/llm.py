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


class ResumeIntakeLLM:
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY)
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC) if self.enabled else None

    def parse_resume(self, *, resume_text: str, resume_url: str, job_description: str) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = self._client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are a resume intake agent. Extract structured candidate data from resume text. "
                "Return strict JSON only with keys: name, email, skills, years_experience, summary. "
                "skills must be an array of lowercase strings. years_experience must be a number."
            ),
            input=(
                f"Job description:\n{job_description}\n\n"
                f"Resume URL:\n{resume_url}\n\n"
                f"Resume text:\n{resume_text}"
            ),
        )
        return _extract_json(response.output_text)
