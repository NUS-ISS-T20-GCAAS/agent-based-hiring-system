import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

RESUME_INTAKE_AGENT_URL = os.getenv("RESUME_INTAKE_AGENT_URL", "http://resume-intake-agent:8000")
SKILL_ASSESSMENT_AGENT_URL = os.getenv("SKILL_ASSESSMENT_AGENT_URL", "http://skill-assessment-agent:8000")
SCREENING_AGENT_URL = os.getenv("SCREENING_AGENT_URL", "http://screening-agent:8000")
RANKING_AGENT_URL = os.getenv("RANKING_AGENT_URL", "http://ranking-agent:8000")
AUDIT_AGENT_URL = os.getenv("AUDIT_AGENT_URL", "http://audit-agent:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
QUEUE_POLL_INTERVAL_SECONDS = float(os.getenv("QUEUE_POLL_INTERVAL_SECONDS", "1.0"))

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "hiring_system")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
