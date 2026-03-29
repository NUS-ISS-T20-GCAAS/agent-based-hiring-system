from typing import List

from fastapi import FastAPI, HTTPException

from app.agent import RankingAgent
from app.config import DEBUG, PORT, SERVICE_NAME
from app.schemas import Artifact, RunRequest
from app.shared_memory import SharedMemory

app = FastAPI(
    title="Ranking Agent Service",
    description="Standalone ranking agent scaffold for future recommendation logic",
    version="0.1.0",
)

shared_memory = SharedMemory()
agent = RankingAgent(agent_type="ranking", shared_memory=shared_memory)


@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "version": "0.1.0",
        "status": "running",
        "agent_type": agent.agent_type,
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
        "artifacts_count": len(shared_memory.all()),
    }


@app.get("/artifacts/{entity_id}", response_model=List[Artifact])
def get_artifacts(entity_id: str):
    return shared_memory.get_by_entity(entity_id)


@app.delete("/artifacts")
def clear_artifacts():
    count = len(shared_memory.all())
    shared_memory.clear()
    return {
        "status": "cleared",
        "artifacts_removed": count,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG,
    )
