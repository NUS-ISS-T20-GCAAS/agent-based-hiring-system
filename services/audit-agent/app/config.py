import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

MIN_AUDIT_SAMPLE_SIZE = int(os.getenv("MIN_AUDIT_SAMPLE_SIZE", "5"))
LOW_SELECTION_RATE_THRESHOLD = float(os.getenv("LOW_SELECTION_RATE_THRESHOLD", "0.2"))

SERVICE_NAME = os.getenv("SERVICE_NAME", "audit-agent")
PORT = int(os.getenv("PORT", "8003"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
