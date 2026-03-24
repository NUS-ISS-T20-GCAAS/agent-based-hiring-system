from fastapi import APIRouter

from app.config import SERVICE_NAME

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}
