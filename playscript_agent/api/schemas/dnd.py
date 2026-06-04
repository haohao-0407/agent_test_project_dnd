from __future__ import annotations

from pydantic import BaseModel, Field


class DiceRequest(BaseModel):
    expression: str = "1d20"
    reason: str = "manual roll"
    rollerId: str | None = None
    advantage: str = "normal"


class TokenMoveRequest(BaseModel):
    tokenId: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class ChatRequest(BaseModel):
    message: str
    speaker: str = "player"
