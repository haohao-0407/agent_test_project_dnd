from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
from playscript_agent.api.schemas import MonsterCreateRequest, MonsterUpdateRequest
from playscript_agent.api.services import monster_repository
from playscript_agent.api.services.game_state import Principal


router = APIRouter()


@router.get("/api/permanent-monsters")
def get_permanent_monsters(principal: Principal = Depends(get_principal)) -> dict:
    try:
        return {"monsters": monster_repository.load_permanent_monsters()}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/permanent-monsters")
def create_permanent_monster(
    request: MonsterCreateRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        monster = monster_repository.create_permanent_monster(request.monster)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"monster": monster, "monsters": monster_repository.load_permanent_monsters()}


@router.patch("/api/permanent-monsters/{monster_id}")
def update_permanent_monster(
    monster_id: str,
    request: MonsterUpdateRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        monster = monster_repository.update_permanent_monster(
            monster_id,
            request.updates,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"monster": monster, "monsters": monster_repository.load_permanent_monsters()}
