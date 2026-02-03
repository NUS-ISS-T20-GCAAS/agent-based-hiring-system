from pydantic import BaseModel
from typing import Dict, Any

class IntakeRequest(BaseModel):
    job_id: str
    payload: Dict[str, Any]

class IntakeResponse(BaseModel):
    job_id: str
    status: str
    output: Dict[str, Any]
