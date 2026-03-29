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

    def active_count(self) -> int:
        with self._lock:
            return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
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
        if self.active_count() == 0:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.broadcast(message))
            return

        try:
            anyio.from_thread.run(self.broadcast, message)
        except RuntimeError:
            return


event_hub = EventHub()


def emit_agent_activity(
    *,
    agent: str,
    message: str,
    correlation_id: str | None = None,
    entity_id: str | None = None,
    candidate_id: str | None = None,
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
