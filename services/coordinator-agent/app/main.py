import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.coordinator import coordinator_llm
from app.repository import CoordinatorRepository
from app.routes import router
from app.events import event_hub, utc_now_iso
from app.workflow_queue import workflow_queue_worker

app = FastAPI(title="Coordinator Agent")

app.include_router(router)


@app.on_event("startup")
def startup_event():
    workflow_queue_worker.start()


@app.on_event("shutdown")
def shutdown_event():
    workflow_queue_worker.stop()


@app.get("/health")
def health():
    health_payload = {
        "status": "ok",
        "service": "coordinator",
        "queue_worker": {
            "running": workflow_queue_worker.is_running(),
            "poll_interval_seconds": workflow_queue_worker.poll_interval_seconds,
        },
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
        health_payload["queue_worker"]["database_available"] = False
    else:
        health_payload["queue_worker"]["database_available"] = True
    return health_payload


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
