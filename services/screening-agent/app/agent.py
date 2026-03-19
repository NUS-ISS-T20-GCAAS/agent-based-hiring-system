from app.base_agent import BaseAgent
from app.llm import ScreeningLLM
from app.worker import coerce_screening_result, heuristic_screen_candidate


class ScreeningAgent(BaseAgent):
    def __init__(self, agent_type, shared_memory):
        super().__init__(agent_type=agent_type, shared_memory=shared_memory)
        self.llm = ScreeningLLM()

    def artifact_type(self) -> str:
        return "qualification_screening_result"

    def handle(self, input_data):
        parsed_resume = input_data.get("parsed_resume") or {}
        job_description = (input_data.get("job_description") or "").lower()

        try:
            llm_result = self.llm.score_candidate(
                parsed_resume=parsed_resume,
                job_description=job_description,
            )
            result = coerce_screening_result(llm_result)
        except Exception as exc:
            self.logger.error("screening_llm_fallback", error=str(exc))
            result = heuristic_screen_candidate(
                parsed_resume=parsed_resume,
                job_description=job_description,
            )

        return {
            "payload": {
                "qualification_score": result["qualification_score"],
                "meets_threshold": result["meets_threshold"],
                "matched_skills": result["matched_skills"],
                "missing_skills": result["missing_skills"][:10],
                "years_experience": result["years_experience"],
            },
            "confidence": result["confidence"],
            "explanation": result["explanation"],
        }
