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


class AuditLLM:
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY)
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC) if self.enabled else None

    def audit(
        self,
        *,
        job_id: str | None,
        stats: dict[str, Any],
        candidates: list[dict[str, Any]],
        decisions: list[dict[str, Any]],
        orchestration_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = self._client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are an audit and compliance agent for a hiring workflow. "
                "Review selection outcomes and produce strict JSON only with keys: "
                "job_id, selection_rate, total_candidates, shortlisted, bias_flags, "
                "risk_level, review_required, recommendations, data_completeness, confidence. "
                "bias_flags and recommendations must be arrays of strings. "
                "risk_level must be one of low, medium, high. "
                "selection_rate and confidence must be numbers from 0 to 1. "
                "Use the provided stats, candidates, and decisions as the source of truth for counts and rates. "
                "If an orchestration_plan is provided, use it as coordinator guidance for what to inspect more carefully, "
                "but do not invent counts or rates that contradict the provided data. "
                "If bias_flags is empty, review_required must be false and risk_level must be low. "
                "If low_selection_rate is present in bias_flags, risk_level must be high. "
                "If bias_flags is non-empty and does not include low_selection_rate, risk_level must be medium or high."
            ),
            input=json.dumps(
                {
                    "job_id": job_id,
                    "stats": stats,
                    "candidates": candidates,
                    "decisions": decisions,
                    "orchestration_plan": orchestration_plan or {},
                }
            ),
        )
        return _extract_json(response.output_text)
