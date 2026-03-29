import os

RESUME_INTAKE_AGENT_URL = os.getenv("RESUME_INTAKE_AGENT_URL", "http://resume-intake-agent:8000")
SCREENING_AGENT_URL = os.getenv("SCREENING_AGENT_URL", "http://screening-agent:8000")
RANKING_AGENT_URL = os.getenv("RANKING_AGENT_URL", "http://ranking-agent:8000")
AUDIT_AGENT_URL = os.getenv("AUDIT_AGENT_URL", "http://audit-agent:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "hiring_system")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
