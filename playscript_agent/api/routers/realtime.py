from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from playscript_agent.api.services.game_state import get_store, resolve_session_token
from playscript_agent.api.services.realtime import state_socket_manager


router = APIRouter()


@router.websocket("/ws/state")
async def state_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    try:
        principal = resolve_session_token(token)
    except KeyError:
        await websocket.close(code=1008)
        return

    await state_socket_manager.connect(principal.session_id, websocket)
    try:
        await state_socket_manager.send_state(
            websocket,
            get_store(principal.session_id).snapshot(),
        )
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        state_socket_manager.disconnect(principal.session_id, websocket)
