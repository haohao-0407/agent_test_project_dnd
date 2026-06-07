from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
from playscript_agent.api.schemas import CharacterCreateRequest, CharacterUpdateRequest
from playscript_agent.api.services import character_repository
from playscript_agent.api.services.game_state import Principal, get_store


router = APIRouter()


@router.get("/api/characters")
def get_characters(principal: Principal = Depends(get_principal)) -> dict:
    return {"characters": get_store(principal.session_id).snapshot()["characters"]}


@router.get("/api/permanent-characters")
def get_permanent_characters(principal: Principal = Depends(get_principal)) -> dict:
    try:
        return {"characters": character_repository.load_permanent_characters()}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/permanent-characters")
def create_permanent_character(
    request: CharacterCreateRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        character = character_repository.create_permanent_character(request.character)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"character": character, "characters": character_repository.load_permanent_characters()}


@router.patch("/api/permanent-characters/{character_id}")
def update_permanent_character(
    character_id: str,
    request: CharacterUpdateRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    try:
        character = character_repository.update_permanent_character(
            character_id,
            request.updates,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"character": character, "characters": character_repository.load_permanent_characters()}


@router.post("/api/characters")
def create_character(request: CharacterCreateRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        character = store.create_character(
            request.character,
            user_id=principal.user_id,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"character": character, "state": store.snapshot()}


@router.patch("/api/characters/{character_id}")
def update_character(
    character_id: str,
    request: CharacterUpdateRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    store = get_store(principal.session_id)
    try:
        character = store.update_character(
            character_id,
            request.updates,
            user_id=principal.user_id,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"character": character, "state": store.snapshot()}
