from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class SharedContext(BaseModel):
    job_id: str
    parsed_resume: Optional[Dict[str, Any]] = None
    audit_log: List[str] = []

# in-memory store (OK for now)
_CONTEXT_STORE: dict[str, SharedContext] = {}

def get_context(job_id: str) -> SharedContext:
    if job_id not in _CONTEXT_STORE:
        _CONTEXT_STORE[job_id] = SharedContext(job_id=job_id)
    return _CONTEXT_STORE[job_id]
