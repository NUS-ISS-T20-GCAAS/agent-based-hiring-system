from fastapi import FastAPI
from app.agent import ResumeIntakeAgent
from app.shared_memory import SharedMemory
from app.schemas import RunRequest, Artifact
from typing import List

app = FastAPI()

shared_memory = SharedMemory()
agent = ResumeIntakeAgent(agent_type="resume_intake", shared_memory=shared_memory)

@app.post("/run", response_model=Artifact)
def run_agent(req: RunRequest):
    artifact = agent.run(
        entity_id=req.entity_id,
        correlation_id=req.correlation_id,
        input_data=req.input_data,
    )
    return artifact

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/artifacts/{entity_id}", response_model=List[Artifact])
def get_artifacts(entity_id: str):
    return shared_memory.get_by_entity(entity_id)
