from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
from playscript_agent.api.schemas import AdventureStartRequest
from playscript_agent.api.services import adventure_service
from playscript_agent.api.services.game_state import Principal


router = APIRouter()


@router.post("/api/adventure/start")
def start_adventure(request: AdventureStartRequest, principal: Principal = Depends(get_principal)) -> dict:
    try:
        state = adventure_service.start_adventure(
            user_id=principal.user_id,
            session_id=principal.session_id,
            module_name=request.moduleName,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"state": state}
