from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import (
    MapBackgroundUpdateRequest,
    MapLayerUpdateRequest,
    MapUpdateRequest,
    TokenMoveRequest,
)
from playscript_agent.api.services import map_service
from playscript_agent.api.services.game_state import game_state


router = APIRouter()


@router.post("/api/token/move")
def move_token(request: TokenMoveRequest) -> dict:
    try:
        map_service.move_token(request.tokenId, request.x, request.y, user_id=request.userId)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"state": game_state.snapshot()}


@router.patch("/api/map")
def update_map(request: MapUpdateRequest) -> dict:
    try:
        map_service.update_map(request.updates, user_id=request.userId)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"state": game_state.snapshot()}


@router.patch("/api/map/layers")
def update_map_layer(request: MapLayerUpdateRequest) -> dict:
    try:
        map_service.edit_map_layer(request.layer, request.items, user_id=request.userId)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"state": game_state.snapshot()}


@router.patch("/api/map/background")
def update_map_background(request: MapBackgroundUpdateRequest) -> dict:
    try:
        map_service.set_map_background(request.background, user_id=request.userId)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"state": game_state.snapshot()}
