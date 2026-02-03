from fastapi import FastAPI
from app.schemas import IntakeRequest, IntakeResponse
from app.worker import process_resume

app = FastAPI(title="Resume Intake Agent")

@app.post("/run", response_model=IntakeResponse)
def run(request: IntakeRequest):
    parsed = process_resume(request.payload)
    return IntakeResponse(
        job_id=request.job_id,
        status="success",
        output={"parsed_resume": parsed}
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "resume-intake"}
