from typing import List

from fastapi import FastAPI, HTTPException

from app.agent import SkillAssessmentAgent
from app.config import DEBUG, PORT, SERVICE_NAME
from app.schemas import Artifact, RunRequest
from app.shared_memory import SharedMemory

app = FastAPI(
    title="Skill Assessment Agent Service",
    description="Skill assessment and gap analysis agent with LLM and heuristic fallback",
    version="1.0.0",
)

shared_memory = SharedMemory()
agent = SkillAssessmentAgent(agent_type="skill_assessment", shared_memory=shared_memory)


@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "agent_type": agent.agent_type,
        "llm_enabled": agent.llm.enabled,
    }


@app.post("/run", response_model=Artifact)
def run_agent(req: RunRequest):
    try:
        return agent.run(
            entity_id=req.entity_id,
            correlation_id=req.correlation_id,
            input_data=req.input_data,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "llm_enabled": agent.llm.enabled,
        "artifacts_count": len(shared_memory.all()),
    }


@app.get("/artifacts/{entity_id}", response_model=List[Artifact])
def get_artifacts(entity_id: str):
    return shared_memory.get_by_entity(entity_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG,
    )
