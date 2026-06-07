from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
from playscript_agent.api.schemas import PendingActionRequest
from playscript_agent.api.services.game_state import Principal, get_store


router = APIRouter()


@router.post("/api/pending-actions/{action_id}/confirm")
def confirm_pending_action(
    action_id: str,
    request: PendingActionRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    store = get_store(principal.session_id)
    try:
        pending_action = store.confirm_pending_action(action_id, user_id=principal.user_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"pendingAction": pending_action, "state": store.snapshot()}


@router.post("/api/pending-actions/{action_id}/decline")
def decline_pending_action(
    action_id: str,
    request: PendingActionRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    store = get_store(principal.session_id)
    try:
        pending_action = store.decline_pending_action(action_id, user_id=principal.user_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"pendingAction": pending_action, "state": store.snapshot()}
