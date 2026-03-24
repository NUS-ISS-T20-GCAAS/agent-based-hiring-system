from fastapi import FastAPI, HTTPException
from typing import List

from app.agent import AuditAgent
from app.shared_memory import SharedMemory
from app.schemas import RunRequest, Artifact
from app.config import SERVICE_NAME, PORT, DEBUG

app = FastAPI(
    title="Audit Agent Service",
    description="Audit and compliance agent with LLM and heuristic fallback",
    version="1.0.0",
)

shared_memory = SharedMemory()
agent = AuditAgent(agent_type="audit", shared_memory=shared_memory)


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


@app.get("/artifacts")
def get_all_artifacts():
    return {
        "count": len(shared_memory.all()),
        "artifacts": shared_memory.all(),
    }


@app.delete("/artifacts")
def clear_artifacts():
    count = len(shared_memory.all())
    shared_memory.clear()
    return {
        "status": "cleared",
        "artifacts_removed": count,
    }


@app.get("/stats")
def get_stats():
    all_artifacts = shared_memory.all()

    if not all_artifacts:
        return {
            "total_processed": 0,
            "review_required": 0,
            "high_risk": 0,
            "avg_selection_rate": 0.0,
            "llm_enabled": agent.llm.enabled,
        }

    total = len(all_artifacts)
    review_required = sum(
        1 for artifact in all_artifacts if artifact.get("payload", {}).get("review_required", False)
    )
    high_risk = sum(
        1 for artifact in all_artifacts if artifact.get("payload", {}).get("risk_level") == "high"
    )
    selection_rates = [artifact.get("payload", {}).get("selection_rate", 0.0) for artifact in all_artifacts]
    avg_selection_rate = sum(selection_rates) / len(selection_rates) if selection_rates else 0.0

    return {
        "total_processed": total,
        "review_required": review_required,
        "high_risk": high_risk,
        "avg_selection_rate": avg_selection_rate,
        "llm_enabled": agent.llm.enabled,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG,
    )
