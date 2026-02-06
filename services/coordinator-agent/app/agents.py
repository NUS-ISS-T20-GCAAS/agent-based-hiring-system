from app.bootstrap import shared_memory
from resume_intake_agent.app.agent import ResumeIntakeAgent

resume_intake_agent = ResumeIntakeAgent(
    agent_type="resume_intake",
    shared_memory=shared_memory,
)
