import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.coordinator import coordinator_llm
from app.repository import CoordinatorRepository
from app.routes import router
from app.events import event_hub, utc_now_iso
from app.config import CELERY_BROKER_URL

# Ensure Celery app is importable so .delay() calls work from routes
import app.celery_app  # noqa: F401

app = FastAPI(title="Coordinator Agent")

app.include_router(router)


def _celery_broker_status() -> dict:
    """Check whether the Celery broker (Redis) is reachable."""
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(CELERY_BROKER_URL, socket_connect_timeout=2)
        r.ping()
        return {"status": "connected", "broker": CELERY_BROKER_URL}
    except Exception as exc:
        return {"status": "disconnected", "broker": CELERY_BROKER_URL, "error": str(exc)}


@app.get("/health")
def health():
    health_payload = {
        "status": "ok",
        "service": "coordinator",
        "celery_broker": _celery_broker_status(),
        "llm_enabled": coordinator_llm.enabled,
    }
    try:
        health_payload["workflow_queue"] = CoordinatorRepository().get_workflow_queue_counts()
    except Exception:
        health_payload["workflow_queue"] = {
            "pending": 0,
            "running": 0,
            "failed": 0,
            "completed": 0,
        }
        health_payload["database_available"] = False
    else:
        health_payload["database_available"] = True
    return health_payload


@app.get("/queue/status")
def queue_status():
    """Return Celery task queue status via broker inspection."""
    broker_info = _celery_broker_status()
    result = {"broker": broker_info}

    try:
        from app.celery_app import celery as celery_app
        inspector = celery_app.control.inspect(timeout=2)

        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        scheduled = inspector.scheduled() or {}

        result["workers"] = {
            "active_tasks": sum(len(v) for v in active.values()),
            "reserved_tasks": sum(len(v) for v in reserved.values()),
            "scheduled_tasks": sum(len(v) for v in scheduled.values()),
            "worker_count": len(active),
            "workers": list(active.keys()),
        }
    except Exception as exc:
        result["workers"] = {"status": "unavailable", "error": str(exc)}

    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await event_hub.connect(websocket)

    await websocket.send_json(
        {
            "type": "connection",
            "data": {
                "service": "coordinator",
                "status": "connected",
                "timestamp": utc_now_iso(),
            },
        }
    )

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if message.strip().lower() == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "data": {"timestamp": utc_now_iso()},
                        }
                    )
            except asyncio.TimeoutError:
                await websocket.send_json(
                    {
                        "type": "heartbeat",
                        "data": {
                            "timestamp": utc_now_iso(),
                            "active_connections": event_hub.active_count(),
                        },
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        event_hub.disconnect(websocket)
