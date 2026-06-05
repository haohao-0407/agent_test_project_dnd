from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import DiceRequest
from playscript_agent.api.services import dice_service
from playscript_agent.api.services.game_state import game_state


router = APIRouter()


@router.post("/api/dice")
def roll_dice(request: DiceRequest) -> dict:
    try:
        if not game_state.can_roll_for_actor(request.userId, request.rollerId):
            raise PermissionError(f"user {request.userId} cannot roll for {request.rollerId}")
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
    return {"result": result, "state": game_state.snapshot()}
