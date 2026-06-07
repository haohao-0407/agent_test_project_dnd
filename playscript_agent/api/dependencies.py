from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Request

from playscript_agent.api.services.game_state import Principal, resolve_session_token


async def get_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing session token")

    try:
        principal = resolve_session_token(token)
    except KeyError:
        raise HTTPException(status_code=401, detail="invalid session token") from None

    request.state.principal = principal
    return principal


def bearer_token_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing or malformed authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing session token")
    return token
