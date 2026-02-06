from pydantic import BaseModel, Field
from typing import Any, Dict

class JobRequest(BaseModel):
    job_id: str
    resume_url: str
    job_description: str

class RunRequest(BaseModel):
    entity_id: str
    correlation_id: str
    input_data: Dict[str, Any]

class Artifact(BaseModel):
    artifact_id: str
    entity_id: str
    correlation_id: str
    agent_id: str
    agent_type: str
    artifact_type: str
    payload: Any = None
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    created_at: str
    version: int = 1
