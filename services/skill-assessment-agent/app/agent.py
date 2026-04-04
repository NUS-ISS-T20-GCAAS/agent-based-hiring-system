from app.base_agent import BaseAgent
from app.llm import SkillAssessmentLLM
from app.worker import coerce_skill_assessment_result, heuristic_assess_skills


class SkillAssessmentAgent(BaseAgent):
    def __init__(self, agent_type, shared_memory):
        super().__init__(agent_type=agent_type, shared_memory=shared_memory)
        self.llm = SkillAssessmentLLM()

    def artifact_type(self) -> str:
        return "skill_assessment_result"

    def handle(self, input_data):
        parsed_resume = input_data.get("parsed_resume") or {}
        resume_text = input_data.get("resume_text") or ""
        job_description = input_data.get("job_description") or ""
        job_requirements = input_data.get("job_requirements") or {}

        method_used = "llm"

        try:
            llm_result = self.llm.assess_skills(
                parsed_resume=parsed_resume,
                resume_text=resume_text,
                job_description=job_description,
                job_requirements=job_requirements,
            )
            result = coerce_skill_assessment_result(llm_result)
        except Exception as exc:
            method_used = "heuristic"
            self.logger.error("skill_assessment_llm_fallback", error=str(exc))
            result = heuristic_assess_skills(
                parsed_resume=parsed_resume,
                resume_text=resume_text,
                job_description=job_description,
                job_requirements=job_requirements,
            )

        explanation = self._build_explanation(result=result, method_used=method_used)

        return {
            "payload": {
                "skills_score": result["skills_score"],
                "confidence": result["confidence"],
                "matched_required_skills": result["matched_required_skills"],
                "matched_preferred_skills": result["matched_preferred_skills"],
                "missing_required_skills": result["missing_required_skills"],
                "missing_preferred_skills": result["missing_preferred_skills"],
                "detected_soft_skills": result["detected_soft_skills"],
                "matched_soft_skills": result["matched_soft_skills"],
                "missing_soft_skills": result["missing_soft_skills"],
                "strengths": result["strengths"],
                "gaps": result["gaps"],
                "gap_analysis": result["gap_analysis"],
                "details": {
                    "method": method_used,
                    "required_matches": len(result["matched_required_skills"]),
                    "preferred_matches": len(result["matched_preferred_skills"]),
                    "soft_skill_matches": len(result["matched_soft_skills"]),
                },
            },
            "confidence": result["confidence"],
            "explanation": explanation,
        }

    def _build_explanation(self, *, result: dict, method_used: str) -> str:
        parts = [f"Skill assessment completed at {result['skills_score']:.1%} using {method_used} analysis."]

        if result["matched_required_skills"]:
            parts.append(f"Matched required skills: {', '.join(result['matched_required_skills'][:6])}.")

        if result["matched_preferred_skills"]:
            parts.append(f"Matched preferred skills: {', '.join(result['matched_preferred_skills'][:6])}.")

        if result["detected_soft_skills"]:
            parts.append(f"Detected soft skills: {', '.join(result['detected_soft_skills'][:4])}.")

        if result["gaps"]:
            parts.append(f"Key gaps: {', '.join(result['gaps'][:6])}.")

        parts.append(f"Gap analysis: {result['gap_analysis']}")
        return " ".join(parts)
