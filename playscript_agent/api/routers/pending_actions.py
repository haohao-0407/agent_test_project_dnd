from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import PendingActionRequest
from playscript_agent.api.services.game_state import game_state


router = APIRouter()


@router.post("/api/pending-actions/{action_id}/confirm")
def confirm_pending_action(action_id: str, request: PendingActionRequest) -> dict:
    try:
        pending_action = game_state.confirm_pending_action(action_id, user_id=request.userId)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"pendingAction": pending_action, "state": game_state.snapshot()}


@router.post("/api/pending-actions/{action_id}/decline")
def decline_pending_action(action_id: str, request: PendingActionRequest) -> dict:
    try:
        pending_action = game_state.decline_pending_action(action_id, user_id=request.userId)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"pendingAction": pending_action, "state": game_state.snapshot()}
