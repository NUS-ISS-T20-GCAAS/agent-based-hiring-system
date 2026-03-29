import os

SERVICE_NAME = os.getenv("SERVICE_NAME", "ranking-agent")
PORT = int(os.getenv("PORT", "8004"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
