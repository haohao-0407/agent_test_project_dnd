from __future__ import annotations

from fastapi import APIRouter

from playscript_agent.api.services.game_state import game_state


router = APIRouter()


@router.get("/api/characters")
def get_characters() -> dict:
    return {"characters": game_state.snapshot()["characters"]}
