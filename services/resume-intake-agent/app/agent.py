from app.base_agent import BaseAgent
from app.worker import process_resume


class ResumeIntakeAgent(BaseAgent):
    def artifact_type(self) -> str:
        return "resume_intake_result"

    def handle(self, input_data):
        parsed_resume = process_resume(input_data)

        return {
            "payload": {
                **parsed_resume,
                "status": "parsed",
            },
            "confidence": 0.86,
            "explanation": "Resume intake agent parsed candidate profile for downstream screening",
        }
