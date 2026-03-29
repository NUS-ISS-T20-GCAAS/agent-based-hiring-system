import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.routes import router
from app.events import event_hub, utc_now_iso

app = FastAPI(title="Coordinator Agent")

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "coordinator"}


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
