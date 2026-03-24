"""
Configuration for Screening Agent
Environment-based settings
"""

import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

# Screening Configuration
QUALIFICATION_THRESHOLD = float(os.getenv("QUALIFICATION_THRESHOLD", "0.6"))
REQUIRED_SKILLS_WEIGHT = float(os.getenv("REQUIRED_SKILLS_WEIGHT", "0.7"))
PREFERRED_SKILLS_WEIGHT = float(os.getenv("PREFERRED_SKILLS_WEIGHT", "0.3"))
EXPERIENCE_BONUS_WEIGHT = float(os.getenv("EXPERIENCE_BONUS_WEIGHT", "0.1"))

# Human review triggers
# Decisions within this band around the threshold are flagged for review
REVIEW_BAND = float(os.getenv("REVIEW_BAND", "0.05"))
# Confidence below this value triggers review regardless of score
REVIEW_CONFIDENCE_FLOOR = float(os.getenv("REVIEW_CONFIDENCE_FLOOR", "0.7"))

# Service Configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "screening-agent")
PORT = int(os.getenv("PORT", "8001"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # "json" or "text"