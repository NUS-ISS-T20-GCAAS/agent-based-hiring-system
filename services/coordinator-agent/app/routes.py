from fastapi import APIRouter
from app.schemas import JobRequest, JobResponse
from app.coordinator import run_job

router = APIRouter()

@router.post("/jobs", response_model=JobResponse)
def submit_job(request: JobRequest):
    return run_job(request)
