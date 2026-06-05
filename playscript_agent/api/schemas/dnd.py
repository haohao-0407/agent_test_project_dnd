from __future__ import annotations

from pydantic import BaseModel, Field


class DiceRequest(BaseModel):
    expression: str = "1d20"
    reason: str = "manual roll"
    rollerId: str | None = None
    advantage: str = "normal"
    userId: str = "player-kael"


class TokenMoveRequest(BaseModel):
    tokenId: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    userId: str = "player-kael"


class MapUpdateRequest(BaseModel):
    userId: str = "dm"
    updates: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str
    speaker: str = "player"
    userId: str = "player-kael"


class CharacterUpdateRequest(BaseModel):
    userId: str = "player-kael"
    updates: dict = Field(default_factory=dict)


class CharacterCreateRequest(BaseModel):
    userId: str = "player-kael"
    character: dict = Field(default_factory=dict)


class RagQueryRequest(BaseModel):
    query: str
    userId: str = "player-kael"
    k: int = Field(default=4, ge=1, le=12)
