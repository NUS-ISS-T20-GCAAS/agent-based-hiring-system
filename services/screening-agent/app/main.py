"""
Main FastAPI application for Screening Agent
"""

from fastapi import FastAPI, HTTPException
from typing import List

from app.agent import ScreeningAgent
from app.shared_memory import SharedMemory
from app.schemas import RunRequest, Artifact
from app.config import SERVICE_NAME, PORT, DEBUG

# Initialize FastAPI app
app = FastAPI(
    title="Screening Agent Service",
    description="Qualification screening agent with LLM and heuristic fallback",
    version="1.0.0"
)

# Initialize shared components
shared_memory = SharedMemory()
agent = ScreeningAgent(agent_type="screening", shared_memory=shared_memory)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "agent_type": agent.agent_type,
        "llm_enabled": agent.llm.enabled
    }


@app.post("/run", response_model=Artifact)
def run_agent(req: RunRequest):
    """
    Execute screening agent on a candidate
    
    Request body:
    {
        "entity_id": "candidate-123",
        "correlation_id": "job-application-456",
        "input_data": {
            "parsed_resume": {
                "skills": ["Python", "SQL", "AWS"],
                "years_experience": 7,
                "education": "Bachelor's"
            },
            "job_description": "Looking for Python developer...",
            "job_requirements": {
                "required_skills": ["Python", "SQL"],
                "preferred_skills": ["AWS"],
                "min_years_experience": 5
            }
        }
    }
    
    Returns: Artifact with screening results
    """
    try:
        artifact = agent.run(
            entity_id=req.entity_id,
            correlation_id=req.correlation_id,
            input_data=req.input_data,
        )
        return artifact
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "llm_enabled": agent.llm.enabled,
        "artifacts_count": len(shared_memory.all())
    }


@app.get("/artifacts/{entity_id}", response_model=List[Artifact])
def get_artifacts(entity_id: str):
    """
    Get all artifacts for a specific entity (candidate)
    
    Args:
        entity_id: The candidate ID
        
    Returns:
        List of artifacts (screening results) for this candidate
    """
    artifacts = shared_memory.get_by_entity(entity_id)
    return artifacts


@app.get("/artifacts")
def get_all_artifacts():
    """
    Get all artifacts in memory
    
    Returns:
        List of all screening artifacts
    """
    return {
        "count": len(shared_memory.all()),
        "artifacts": shared_memory.all()
    }


@app.delete("/artifacts")
def clear_artifacts():
    """
    Clear all artifacts from memory (for testing)
    
    Returns:
        Confirmation message
    """
    count = len(shared_memory.all())
    shared_memory.clear()
    return {
        "status": "cleared",
        "artifacts_removed": count
    }


@app.get("/stats")
def get_stats():
    """
    Get agent statistics
    
    Returns:
        Statistics about agent processing
    """
    all_artifacts = shared_memory.all()
    
    if not all_artifacts:
        return {
            "total_processed": 0,
            "passed": 0,
            "failed": 0,
            "avg_score": 0.0,
            "llm_enabled": agent.llm.enabled
        }
    
    # Calculate statistics
    total = len(all_artifacts)
    passed = sum(
        1 for a in all_artifacts 
        if a.get("payload", {}).get("meets_threshold", False)
    )
    failed = total - passed
    
    # Average qualification score
    scores = [
        a.get("payload", {}).get("qualification_score", 0) 
        for a in all_artifacts
    ]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    return {
        "total_processed": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total > 0 else 0.0,
        "avg_score": avg_score,
        "llm_enabled": agent.llm.enabled
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG
    )