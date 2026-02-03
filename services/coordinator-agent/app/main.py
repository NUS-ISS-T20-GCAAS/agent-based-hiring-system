from fastapi import FastAPI
from app.coordinator import CoordinatorAgent
from app.schemas import CoordinateRequest

app = FastAPI(title="Coordinator Agent")

coordinator = CoordinatorAgent()

@app.post("/coordinate")
def coordinate(request: CoordinateRequest):
    return coordinator.handle(request)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "coordinator-agent"
    }    
