from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Header, HTTPException, Request

from playscript_agent.api.services.game_state import Principal, resolve_session_token


SESSION_TOKEN_COOKIE = "dnd-seat-token"


async def get_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_TOKEN_COOKIE)] = None,
) -> Principal:
    token = session_token_from_auth(authorization, session_cookie)

    try:
        principal = resolve_session_token(token)
    except KeyError:
        raise HTTPException(status_code=401, detail="invalid session token") from None

    request.state.principal = principal
    return principal


def bearer_token_from_header(authorization: str | None) -> str:
    return session_token_from_auth(authorization, None)


def session_token_from_auth(authorization: str | None, session_cookie: str | None) -> str:
    if not authorization and session_cookie:
        token = session_cookie.strip()
        if not token:
            raise HTTPException(status_code=401, detail="missing session token")
        return token

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing session token")
    return token
