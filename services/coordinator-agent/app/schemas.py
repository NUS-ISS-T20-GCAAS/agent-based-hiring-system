from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JobRequest(BaseModel):
    job_id: str
    resume_url: str
    job_description: str
    resume_text: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years_experience: Optional[int] = None
    education_level: Optional[str] = None

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

class JobResponse(BaseModel):
    job_id: str
    status: str
    artifact_id: str
    correlation_id: str
