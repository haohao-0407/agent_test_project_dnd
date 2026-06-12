from __future__ import annotations

import asyncio
from threading import RLock
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from playscript_agent.api.services.game_state import get_store


class StateSocketManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._connections: dict[str, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._loop = asyncio.get_running_loop()
            self._connections.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        with self._lock:
            connections = self._connections.get(session_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(session_id, None)

    async def send_state(self, websocket: WebSocket, state: dict[str, Any]) -> None:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "state", "state": state})

    def broadcast_state(self, session_id: str, state: dict[str, Any] | None = None) -> None:
        with self._lock:
            loop = self._loop
            connections = tuple(self._connections.get(session_id, ()))
        if loop is None or not connections:
            return
        payload = state if state is not None else get_store(session_id).snapshot()
        asyncio.run_coroutine_threadsafe(
            self._broadcast_to_connections(session_id, connections, payload),
            loop,
        )

    async def _broadcast_to_connections(
        self,
        session_id: str,
        connections: tuple[WebSocket, ...],
        state: dict[str, Any],
    ) -> None:
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await self.send_state(websocket, state)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session_id, websocket)


state_socket_manager = StateSocketManager()


def notify_state_changed(session_id: str = "default", state: dict[str, Any] | None = None) -> None:
    state_socket_manager.broadcast_state(session_id, state)
