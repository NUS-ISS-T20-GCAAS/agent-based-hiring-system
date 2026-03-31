from app.base_agent import BaseAgent
from app.llm import ScreeningLLM
from app.worker import coerce_screening_result, heuristic_screen_candidate
from app.config import QUALIFICATION_THRESHOLD, REVIEW_BAND, REVIEW_CONFIDENCE_FLOOR


class ScreeningAgent(BaseAgent):
    """
    Qualification Screening Agent
    Evaluates candidates against job requirements using LLM with heuristic fallback
    """
    
    def __init__(self, agent_type, shared_memory):
        super().__init__(agent_type=agent_type, shared_memory=shared_memory)
        self.llm = ScreeningLLM()

    def artifact_type(self) -> str:
        """Returns the artifact type for qualification screening results"""
        return "qualification_screening_result"

    def handle(self, input_data):
        """
        Core screening logic
        
        Input format:
        {
            "parsed_resume": {
                "skills": ["Python", "SQL", "AWS"],
                "years_experience": 7,
                "education": "Bachelor's",
                ...
            },
            "job_description": "Looking for Python developer with SQL...",
            "job_requirements": {  # Optional structured requirements
                "required_skills": ["Python", "SQL"],
                "preferred_skills": ["AWS"],
                "min_years_experience": 5
            }
        }
        
        Returns:
        {
            "payload": {
                "qualification_score": 0.85,
                "meets_threshold": True,
                "matched_skills": ["python", "sql", "aws"],
                "missing_skills": ["docker"],
                "years_experience": 7,
                "decision": "PASS",
                "details": {...}
            },
            "confidence": 0.90,
            "explanation": "Candidate matches 3/4 required skills..."
        }
        """
        parsed_resume = input_data.get("parsed_resume") or {}
        job_description = (input_data.get("job_description") or "").lower()
        job_requirements = input_data.get("job_requirements") or {}

        # Track which method was used
        method_used = "llm"
        
        try:
            # Try LLM-powered screening first
            self.logger.info(
                "screening_llm_attempt",
                candidate_skills=parsed_resume.get("skills", []),
                job_desc_length=len(job_description)
            )
            
            llm_result = self.llm.score_candidate(
                parsed_resume=parsed_resume,
                job_description=job_description,
                job_requirements=job_requirements
            )
            
            result = coerce_screening_result(llm_result)
            
            self.logger.info(
                "screening_llm_success",
                qualification_score=result["qualification_score"],
                meets_threshold=result["meets_threshold"]
            )
            
        except Exception as exc:
            # Fallback to rule-based heuristic
            method_used = "heuristic"
            
            self.logger.error("screening_llm_fallback", error=str(exc))
            
            result = heuristic_screen_candidate(
                parsed_resume=parsed_resume,
                job_description=job_description,
                job_requirements=job_requirements
            )
            
            self.logger.info(
                "screening_heuristic_used",
                qualification_score=result["qualification_score"],
                meets_threshold=result["meets_threshold"]
            )

        # Enhance result with additional decision info
        decision = "PASS" if result["meets_threshold"] else "FAIL"

        # ── Human review flag ────────────────────────────────────────────────
        # Flag for human review when any of these conditions are true:
        #   1. Score is within REVIEW_BAND of the threshold (borderline case)
        #   2. Confidence is below REVIEW_CONFIDENCE_FLOOR (uncertain result)
        #   3. LLM was unavailable and heuristic was used instead
        needs_human_review = (
            abs(result["qualification_score"] - QUALIFICATION_THRESHOLD) <= REVIEW_BAND
            or result["confidence"] < REVIEW_CONFIDENCE_FLOOR
            or method_used == "heuristic"
        )

        review_reasons = []
        if abs(result["qualification_score"] - QUALIFICATION_THRESHOLD) <= REVIEW_BAND:
            review_reasons.append(
                f"score {result['qualification_score']:.0%} is within "
                f"{REVIEW_BAND:.0%} of threshold {QUALIFICATION_THRESHOLD:.0%}"
            )
        if result["confidence"] < REVIEW_CONFIDENCE_FLOOR:
            review_reasons.append(
                f"confidence {result['confidence']:.0%} below floor "
                f"{REVIEW_CONFIDENCE_FLOOR:.0%}"
            )
        if method_used == "heuristic":
            review_reasons.append("LLM unavailable — heuristic fallback used")
        # ─────────────────────────────────────────────────────────────────────

        # Build detailed explanation
        explanation = self._build_explanation(
            result,
            decision=decision,
            method_used=method_used,
            needs_human_review=needs_human_review,
            review_reasons=review_reasons,
        )

        return {
            "payload": {
                "qualification_score": result["qualification_score"],
                "meets_threshold": result["meets_threshold"],
                "matched_skills": result["matched_skills"],
                "missing_skills": result["missing_skills"][:10],
                "years_experience": result["years_experience"],
                "decision": decision,
                "needs_human_review": needs_human_review,
                "review_reasons": review_reasons,
                "details": {
                    "total_matched": len(result["matched_skills"]),
                    "total_missing": len(result["missing_skills"]),
                    "threshold_used": QUALIFICATION_THRESHOLD,
                    "review_band": REVIEW_BAND,
                    "confidence_floor": REVIEW_CONFIDENCE_FLOOR,
                    "method": method_used,
                },
            },
            "confidence": result["confidence"],
            "explanation": explanation,
        }

    def _build_explanation(
        self,
        result: dict,
        *,
        decision: str,
        method_used: str,
        needs_human_review: bool,
        review_reasons: list[str],
    ) -> str:
        """Build human-readable explanation"""
        parts = [f"Decision {decision} at {result['qualification_score']:.1%} using {method_used} screening."]

        experience_years = result["years_experience"]
        parts.append(f"Experience: {experience_years} year{'s' if experience_years != 1 else ''}.")

        if result["matched_skills"]:
            parts.append(f"Matched skills: {', '.join(result['matched_skills'][:6])}.")

        if result["missing_skills"]:
            parts.append(f"Missing skills: {', '.join(result['missing_skills'][:6])}.")

        if result.get("explanation"):
            parts.append(f"Analysis: {result['explanation']}")

        if needs_human_review:
            review_note = ", ".join(review_reasons[:3]) if review_reasons else "manual review requested"
            parts.append(f"Human review required because {review_note}.")

        return " ".join(parts)
