import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

REQUIRED_SKILLS_WEIGHT = float(os.getenv("SKILL_REQUIRED_WEIGHT", "0.75"))
PREFERRED_SKILLS_WEIGHT = float(os.getenv("SKILL_PREFERRED_WEIGHT", "0.15"))
SOFT_SKILLS_WEIGHT = float(os.getenv("SKILL_SOFT_WEIGHT", "0.10"))

SERVICE_NAME = os.getenv("SERVICE_NAME", "skill-assessment-agent")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
