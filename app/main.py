from fastapi import FastAPI

app = FastAPI(title="Agentic Hiring System")

@app.get("/health")
def health():
    return {"status": "ok"}
