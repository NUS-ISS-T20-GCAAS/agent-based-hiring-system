# app/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    print("Health check endpoint called.")
    return {"status": "ok"}
