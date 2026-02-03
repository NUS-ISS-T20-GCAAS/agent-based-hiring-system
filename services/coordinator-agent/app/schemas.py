from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CoordinateRequest(BaseModel):
    candidate_data: Dict[str, Any]  # structured resume data
    job_id: str                      # the target job identifier
    tasks: Optional[List[str]] = None  # list of agent tasks to run
    metadata: Optional[Dict[str, Any]] = None  # optional info like timestamps, requestor, etc.
