from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
from playscript_agent.api.schemas import DiceRequest
from playscript_agent.api.services import dice_service
from playscript_agent.api.services.game_state import Principal, get_store


router = APIRouter()


@router.post("/api/dice")
def roll_dice(request: DiceRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        if not store.can_roll_for_actor(principal.user_id, request.rollerId):
            raise PermissionError(f"user {principal.user_id} cannot roll for {request.rollerId}")
        result = dice_service.roll_and_record(
            request.expression,
            reason=request.reason,
            roller_id=request.rollerId,
            advantage=request.advantage,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"result": result, "state": store.snapshot()}
