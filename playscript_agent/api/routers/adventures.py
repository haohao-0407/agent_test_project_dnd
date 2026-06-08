from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
from playscript_agent.api.schemas import AdventureReadyRequest, AdventureSceneJumpRequest, AdventureStartRequest
from playscript_agent.api.services import adventure_service
from playscript_agent.api.services.game_state import Principal


router = APIRouter()


def _raise_http(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


@router.get("/api/adventure/scenes")
def list_adventure_scenes(
    moduleName: str = "凡戴尔的失落矿坑",
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        scenes = adventure_service.scene_browser(moduleName)
    except Exception as error:
        _raise_http(error)
    return {"scenes": scenes}


@router.post("/api/adventure/start")
def start_adventure(request: AdventureStartRequest, principal: Principal = Depends(get_principal)) -> dict:
    try:
        state = adventure_service.start_adventure(
            user_id=principal.user_id,
            session_id=principal.session_id,
            module_name=request.moduleName,
        )
    except Exception as error:
        _raise_http(error)
    return {"state": state}


@router.post("/api/adventure/ready")
def set_player_ready(request: AdventureReadyRequest, principal: Principal = Depends(get_principal)) -> dict:
    try:
        state = adventure_service.set_player_ready(
            user_id=principal.user_id,
            session_id=principal.session_id,
            module_name=request.moduleName,
            ready=request.ready,
        )
    except Exception as error:
        _raise_http(error)
    return {"state": state}


@router.post("/api/adventure/scenes/jump")
def jump_adventure_scene(request: AdventureSceneJumpRequest, principal: Principal = Depends(get_principal)) -> dict:
    try:
        state = adventure_service.switch_exploration_scene(
            user_id=principal.user_id,
            session_id=principal.session_id,
            module_name=request.moduleName,
            scene_id=request.sceneId,
        )
    except Exception as error:
        _raise_http(error)
    return {"state": state}
