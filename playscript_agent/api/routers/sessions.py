from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response

from playscript_agent.api.dependencies import SESSION_TOKEN_COOKIE, get_principal, session_token_from_auth
from playscript_agent.api.schemas import JoinRequest
from playscript_agent.api.services.game_state import (
    Principal,
    SESSION_TOKEN_TTL,
    get_store,
    join_session,
    resolve_session_token,
    revoke_session_token,
)
from playscript_agent.api.services.realtime import notify_state_changed


router = APIRouter()


@router.get("/api/state")
def get_state(principal: Principal = Depends(get_principal)) -> dict:
    return get_store(principal.session_id).snapshot()


@router.post("/api/auth/join")
def join(
    request: JoinRequest,
    response: Response,
) -> dict:
    try:
        session_token = join_session(role=request.role, username=request.username)
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    _set_session_cookie(response, session_token.token)
    notify_state_changed(session_token.principal.session_id)
    return _auth_payload(session_token.token, session_token.principal)


@router.get("/api/auth/me")
def me(principal: Principal = Depends(get_principal)) -> dict:
    return _auth_payload(None, principal)


@router.post("/api/auth/logout")
def logout(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_TOKEN_COOKIE)] = None,
) -> dict:
    token = session_token_from_auth(authorization, session_cookie)
    try:
        principal = resolve_session_token(token)
    except KeyError:
        principal = None
    revoke_session_token(token)
    if principal is not None:
        notify_state_changed(principal.session_id)
    response.delete_cookie(SESSION_TOKEN_COOKIE, path="/")
    return {"ok": True}


def _auth_payload(token: str | None, principal: Principal) -> dict:
    state = get_store(principal.session_id).snapshot()
    payload = {
        "sessionId": principal.session_id,
        "userId": principal.user_id,
        "role": principal.role,
        "player": _player_for_principal(state, principal),
        "state": state,
    }
    if token is not None:
        payload["token"] = token
    return payload


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_TOKEN_COOKIE,
        token,
        httponly=True,
        max_age=int(SESSION_TOKEN_TTL.total_seconds()),
        path="/",
        samesite="lax",
    )


def _player_for_principal(state: dict, principal: Principal) -> dict | None:
    for player in state["players"]:
        if player["id"] == principal.user_id:
            return player
    return None
