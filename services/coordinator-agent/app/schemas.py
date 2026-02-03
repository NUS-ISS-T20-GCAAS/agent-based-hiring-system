from pydantic import BaseModel
from typing import Optional, Dict, Any

class JobRequest(BaseModel):
    job_id: str
    resume_url: str
    job_description: str

class JobResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
