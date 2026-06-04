from __future__ import annotations

from fastapi import APIRouter

from playscript_agent.api.services.game_state import game_state


router = APIRouter()


@router.get("/api/state")
def get_state() -> dict:
    return game_state.snapshot()
