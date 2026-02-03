import time
import requests
from app.schemas import JobRequest, JobResponse
from app.state import get_context
from app.config import RESUME_INTAKE_AGENT_URL, REQUEST_TIMEOUT

MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds

def run_job(request: JobRequest) -> JobResponse:
    context = get_context(request.job_id)
    context.audit_log.append("Job received")

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                RESUME_INTAKE_AGENT_URL,
                json={
                    "job_id": request.job_id,
                    "payload": {
                        "resume_url": request.resume_url,
                        "job_description": request.job_description
                    }
                },
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            context.audit_log.append(
                f"Resume intake attempt {attempt} failed: {str(e)}"
            )
            time.sleep(RETRY_DELAY)
    else:
        # All retries failed
        raise RuntimeError(
            f"Resume intake agent unavailable after {MAX_RETRIES} retries"
        ) from last_error

    data = response.json()
    context.parsed_resume = data["output"]["parsed_resume"]
    context.audit_log.append("Resume intake completed")

    return JobResponse(
        job_id=request.job_id,
        status="completed",
        result=context.parsed_resume
    )
