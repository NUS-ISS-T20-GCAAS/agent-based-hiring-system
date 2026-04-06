from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import anyio
from fastapi import WebSocket


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def active_count(self) -> int:
        with self._lock:
            return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        loop = asyncio.get_running_loop()
        with self._lock:
            self._loop = loop
            self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        with self._lock:
            connections = list(self._connections)

        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)

        if stale:
            with self._lock:
                for websocket in stale:
                    self._connections.discard(websocket)

    def publish(self, message: dict[str, Any]) -> None:
        """Publish message. Always pushes to Redis PubSub if available."""
        import json
        import redis
        from app.config import CELERY_BROKER_URL

        # Push to Redis so any process (like celery) can send to the FastAPI websockets
        try:
            r = redis.Redis.from_url(CELERY_BROKER_URL, socket_connect_timeout=2)
            r.publish("coordinator_events", json.dumps(message))
            r.close()
        except Exception:
            # Fallback to local push if Redis is somehow unavailable
            pass

    async def start_redis_listener(self) -> None:
        """Background task for FastAPI to listen to Redis and broadcast to websockets."""
        import json
        from redis import asyncio as aioredis
        from app.config import CELERY_BROKER_URL

        try:
            r = aioredis.from_url(CELERY_BROKER_URL)
            pubsub = r.pubsub()
            await pubsub.subscribe("coordinator_events")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast(data)
                    except Exception:
                        pass
        except Exception:
            pass



event_hub = EventHub()


def emit_agent_activity(
    *,
    agent: str,
    message: str,
    correlation_id: str | None = None,
    entity_id: str | None = None,
    candidate_id: str | None = None,
    event_id: str | None = None,
    event_kind: str | None = None,
    stage: str | None = None,
    direction: str | None = None,
    from_agent: str | None = None,
    to_agent: str | None = None,
    artifact_type: str | None = None,
    payload_preview: dict[str, Any] | None = None,
    confidence: float | None = None,
) -> None:
    event_hub.publish(
        {
            "type": "agent_activity",
            "data": {
                "agent": agent,
                "message": message,
                "timestamp": utc_now_iso(),
                "correlation_id": correlation_id,
                "entity_id": entity_id,
                "candidate_id": candidate_id,
                "event_id": event_id,
                "event_kind": event_kind or "status",
                "stage": stage,
                "direction": direction,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "artifact_type": artifact_type,
                "payload_preview": payload_preview or {},
                "confidence": confidence,
            },
        }
    )


def emit_candidate_update(
    *,
    job_id: str,
    candidate_id: str | None = None,
    status: str | None = None,
    correlation_id: str | None = None,
) -> None:
    event_hub.publish(
        {
            "type": "candidate_update",
            "data": {
                "job_id": job_id,
                "candidate_id": candidate_id,
                "status": status,
                "timestamp": utc_now_iso(),
                "correlation_id": correlation_id,
            },
        }
    )
