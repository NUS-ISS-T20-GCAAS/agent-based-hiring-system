from app.base_agent import BaseAgent
from app.llm import AuditLLM
from app.worker import heuristic_audit_check, normalize_audit_result


class AuditAgent(BaseAgent):
    def __init__(self, agent_type, shared_memory):
        super().__init__(agent_type=agent_type, shared_memory=shared_memory)
        self.llm = AuditLLM()

    def artifact_type(self) -> str:
        return "audit_bias_check_result"

    def handle(self, input_data):
        method_used = "llm"
        stats = input_data.get("stats") or {}
        candidates = input_data.get("candidates") or []
        decisions = input_data.get("decisions") or []
        job_id = input_data.get("job_id")
        orchestration_plan = input_data.get("orchestration_plan") or {}

        try:
            raw_result = self.llm.audit(
                job_id=job_id,
                stats=stats,
                candidates=candidates,
                decisions=decisions,
                orchestration_plan=orchestration_plan,
            )
        except Exception as exc:
            method_used = "heuristic"
            self.logger.error("audit_llm_fallback", error=str(exc))
            raw_result = heuristic_audit_check(
                job_id=job_id,
                stats=stats,
                candidates=candidates,
                decisions=decisions,
            )

        result = normalize_audit_result(
            result=raw_result,
            job_id=job_id,
            stats=stats,
            candidates=candidates,
            decisions=decisions,
        )
        explanation = self._build_explanation(result, method_used)

        return {
            "payload": {
                "job_id": result["job_id"],
                "selection_rate": result["selection_rate"],
                "total_candidates": result["total_candidates"],
                "shortlisted": result["shortlisted"],
                "bias_flags": result["bias_flags"],
                "risk_level": result["risk_level"],
                "review_required": result["review_required"],
                "recommendations": result["recommendations"],
                "details": {
                    "method": method_used,
                    "data_completeness": result["data_completeness"],
                },
            },
            "confidence": result["confidence"],
            "explanation": explanation,
        }

    def _build_explanation(self, result: dict, method_used: str) -> str:
        flags = ", ".join(result["bias_flags"]) if result["bias_flags"] else "none"
        recommendations = "; ".join(result["recommendations"][:2]) if result["recommendations"] else "no immediate action"
        review_note = (
            "Manual audit review is required."
            if result["review_required"]
            else "No manual audit review is required."
        )
        return (
            f"Audit completed using {method_used} analysis. "
            f"Risk level is {result['risk_level']} with a selection rate of {result['selection_rate']:.1%} "
            f"across {result['total_candidates']} candidates. "
            f"Bias flags: {flags}. "
            f"{review_note} "
            f"Recommended next steps: {recommendations}."
        )
