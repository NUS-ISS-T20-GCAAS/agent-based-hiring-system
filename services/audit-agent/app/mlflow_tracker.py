"""
MLflow experiment tracking for LLM calls.

Provides a thin wrapper that logs each LLM invocation as an MLflow run,
capturing model name, temperature, prompt version hash, token counts,
latency, and correlation metadata (job_id, agent_name, correlation_id).

Guarded behind MLFLOW_TRACKING_URI — if the env var is unset, all
logging calls are no-ops.
"""

from __future__ import annotations

import hashlib
import os
import time
from contextlib import contextmanager
from typing import Any, Generator

_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")

try:
    import mlflow
except ImportError:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]


def _is_enabled() -> bool:
    return bool(_TRACKING_URI and mlflow is not None)


def _prompt_hash(prompt: str) -> str:
    """Short SHA-256 hash for prompt version tracking."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


@contextmanager
def track_llm_call(
    *,
    agent_name: str,
    model: str,
    prompt_text: str,
    job_id: str | None = None,
    correlation_id: str | None = None,
    temperature: float | None = None,
    extra_params: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager that wraps an LLM call with MLflow logging.

    Usage::

        with track_llm_call(agent_name="screening", model="gpt-4o-mini",
                            prompt_text=system_prompt) as tracker:
            response = openai_client.chat(...)
            tracker["output_text"] = response.output_text
            tracker["token_count"] = response.usage.total_tokens

    The tracker dict is yielded so callers can add metrics after the call.
    """
    tracker: dict[str, Any] = {}
    start = time.monotonic()

    try:
        yield tracker
    finally:
        elapsed = time.monotonic() - start
        if _is_enabled():
            _log_run(
                agent_name=agent_name,
                model=model,
                prompt_text=prompt_text,
                job_id=job_id,
                correlation_id=correlation_id,
                temperature=temperature,
                elapsed_seconds=elapsed,
                extra_params=extra_params or {},
                tracker=tracker,
            )


def _log_run(
    *,
    agent_name: str,
    model: str,
    prompt_text: str,
    job_id: str | None,
    correlation_id: str | None,
    temperature: float | None,
    elapsed_seconds: float,
    extra_params: dict[str, Any],
    tracker: dict[str, Any],
) -> None:
    """Log a completed LLM call as an MLflow run."""
    try:
        mlflow.set_tracking_uri(_TRACKING_URI)
        mlflow.set_experiment(f"hiring-system/{agent_name}")

        with mlflow.start_run(run_name=f"{agent_name}-call"):
            # Parameters
            mlflow.log_param("model", model)
            mlflow.log_param("prompt_version", _prompt_hash(prompt_text))
            mlflow.log_param("agent_name", agent_name)

            if temperature is not None:
                mlflow.log_param("temperature", temperature)
            if job_id:
                mlflow.log_param("job_id", job_id)
            if correlation_id:
                mlflow.log_param("correlation_id", correlation_id)

            for key, value in extra_params.items():
                mlflow.log_param(key, value)

            # Metrics
            mlflow.log_metric("latency_seconds", round(elapsed_seconds, 3))

            if "token_count" in tracker:
                mlflow.log_metric("total_tokens", tracker["token_count"])
            if "confidence" in tracker:
                mlflow.log_metric("confidence", tracker["confidence"])

            # Tags
            mlflow.set_tag("agent", agent_name)
            mlflow.set_tag("model_family", model.split("-")[0] if model else "unknown")

    except Exception:
        # MLflow logging must never break the main workflow
        pass
