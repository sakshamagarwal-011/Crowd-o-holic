from __future__ import annotations

"""
Centralized WebSocket connection manager.
One manager handles all simulation subscriptions.
Components never open their own connections.
"""

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

log = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages all WebSocket connections grouped by simulation_id.
    Thread-safe for asyncio contexts.
    """

    def __init__(self):
        # simulation_id → set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, simulation_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[simulation_id].add(websocket)
        log.info("WS connected | sim=%s total=%d", simulation_id, self.count(simulation_id))

    async def disconnect(self, websocket: WebSocket, simulation_id: str) -> None:
        async with self._lock:
            self._connections[simulation_id].discard(websocket)
            if not self._connections[simulation_id]:
                del self._connections[simulation_id]
        log.info("WS disconnected | sim=%s remaining=%d", simulation_id, self.count(simulation_id))

    def count(self, simulation_id: str) -> int:
        return len(self._connections.get(simulation_id, set()))

    async def broadcast(self, simulation_id: str, message: dict) -> None:
        """Broadcast a message to all connections subscribed to simulation_id."""
        connections = set(self._connections.get(simulation_id, set()))
        if not connections:
            return

        payload = json.dumps(message, default=str)
        dead: set[WebSocket] = set()

        for ws in connections:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections[simulation_id].discard(ws)

    async def send_to(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a single WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            log.warning("Failed to send WS message: %s", e)

    def all_simulation_ids(self) -> list[str]:
        return list(self._connections.keys())


# Singleton — used across the application
connection_manager = ConnectionManager()
