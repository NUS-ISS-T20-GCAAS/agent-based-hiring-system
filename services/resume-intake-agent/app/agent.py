from app.base_agent import BaseAgent


class ResumeIntakeAgent(BaseAgent):
    def artifact_type(self) -> str:
        return "resume_intake_result"

    def handle(self, input_data):
        # Phase 1: NO real parsing yet
        # Just prove the pipeline works

        resume_url = input_data.get("resume_url")

        return {
            "payload": {
                "resume_url": resume_url,
                "status": "received"
            },
            "confidence": 1.0,
            "explanation": "Resume intake agent received the resume successfully"
        }
