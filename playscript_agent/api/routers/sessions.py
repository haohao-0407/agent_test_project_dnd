from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from playscript_agent.api.dependencies import bearer_token_from_header, get_principal
from playscript_agent.api.schemas import JoinRequest
from playscript_agent.api.services.game_state import (
    Principal,
    get_store,
    join_session,
    revoke_session_token,
)


router = APIRouter()


@router.get("/api/state")
def get_state(principal: Principal = Depends(get_principal)) -> dict:
    return get_store(principal.session_id).snapshot()


@router.post("/api/auth/join")
def join(request: JoinRequest) -> dict:
    try:
        session_token = join_session(role=request.role)
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    principal = session_token.principal
    state = get_store(principal.session_id).snapshot()
    return {
        "token": session_token.token,
        "sessionId": principal.session_id,
        "userId": principal.user_id,
        "role": principal.role,
        "player": _player_for_principal(state, principal),
        "state": state,
    }


@router.get("/api/auth/me")
def me(principal: Principal = Depends(get_principal)) -> dict:
    state = get_store(principal.session_id).snapshot()
    return {
        "sessionId": principal.session_id,
        "userId": principal.user_id,
        "role": principal.role,
        "player": _player_for_principal(state, principal),
        "state": state,
    }


@router.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    token = bearer_token_from_header(authorization)
    revoke_session_token(token)
    return {"ok": True}


def _player_for_principal(state: dict, principal: Principal) -> dict | None:
    for player in state["players"]:
        if player["id"] == principal.user_id:
            return player
    return None
