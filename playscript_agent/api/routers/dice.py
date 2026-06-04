from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import DiceRequest
from playscript_agent.api.services import dice_service
from playscript_agent.api.services.game_state import game_state


router = APIRouter()


@router.post("/api/dice")
def roll_dice(request: DiceRequest) -> dict:
    try:
        result = dice_service.roll_and_record(
            request.expression,
            reason=request.reason,
            roller_id=request.rollerId,
            advantage=request.advantage,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"result": result, "state": game_state.snapshot()}
