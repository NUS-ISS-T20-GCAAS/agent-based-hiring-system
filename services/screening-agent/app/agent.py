from app.base_agent import BaseAgent
from app.llm import ScreeningLLM
from app.worker import coerce_screening_result, heuristic_screen_candidate


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
        
        # Build detailed explanation
        explanation = self._build_explanation(result, decision)

        return {
            "payload": {
                "qualification_score": result["qualification_score"],
                "meets_threshold": result["meets_threshold"],
                "matched_skills": result["matched_skills"],
                "missing_skills": result["missing_skills"][:10],  # Limit to top 10
                "years_experience": result["years_experience"],
                "decision": decision,
                "details": {
                    "total_matched": len(result["matched_skills"]),
                    "total_missing": len(result["missing_skills"]),
                    "threshold_used": 0.6,
                    "method": "llm" if "llm" not in str(exc) else "heuristic"
                }
            },
            "confidence": result["confidence"],
            "explanation": explanation,
        }

    def _build_explanation(self, result: dict, decision: str) -> str:
        """Build human-readable explanation"""
        parts = [
            f"Decision: {decision} with qualification score of {result['qualification_score']:.1%}",
            f"Matched skills: {len(result['matched_skills'])}",
            f"Experience: {result['years_experience']} years"
        ]
        
        if result["matched_skills"]:
            parts.append(f"✓ Skills matched: {', '.join(result['matched_skills'][:5])}")
        
        if result["missing_skills"]:
            parts.append(f"✗ Skills missing: {', '.join(result['missing_skills'][:5])}")
        
        if result.get("explanation"):
            parts.append(f"Analysis: {result['explanation']}")
        
        return " | ".join(parts)