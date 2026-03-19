from app.base_agent import BaseAgent
from app.llm import ResumeIntakeLLM
from app.worker import coerce_resume_result, process_resume


class ResumeIntakeAgent(BaseAgent):
    def __init__(self, agent_type, shared_memory):
        super().__init__(agent_type=agent_type, shared_memory=shared_memory)
        self.llm = ResumeIntakeLLM()

    def artifact_type(self) -> str:
        return "resume_intake_result"

    def handle(self, input_data):
        resume_text = input_data.get("resume_text") or ""
        resume_url = input_data.get("resume_url") or ""
        job_description = input_data.get("job_description") or ""

        fallback_resume = process_resume(input_data)

        try:
            llm_result = self.llm.parse_resume(
                resume_text=resume_text,
                resume_url=resume_url,
                job_description=job_description,
            )
            parsed_resume = coerce_resume_result(llm_result, resume_url=resume_url)
            explanation = "Resume intake agent parsed candidate profile with OpenAI model"
            confidence = 0.9
        except Exception as exc:
            self.logger.error("resume_intake_llm_fallback", error=str(exc))
            parsed_resume = coerce_resume_result(fallback_resume, resume_url=resume_url)
            explanation = "Resume intake agent parsed candidate profile with heuristic fallback"
            confidence = 0.72

        return {
            "payload": {
                **parsed_resume,
                "status": "parsed",
            },
            "confidence": confidence,
            "explanation": explanation,
        }
