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


class MapLayerUpdateRequest(BaseModel):
    userId: str = "dm"
    layer: str
    items: list[dict] = Field(default_factory=list)


class MapBackgroundUpdateRequest(BaseModel):
    userId: str = "dm"
    background: dict = Field(default_factory=dict)


class CombatStartRequest(BaseModel):
    userId: str = "dm"
    participantIds: list[str] | None = None


class CombatTurnRequest(BaseModel):
    userId: str = "player-kael"
    actorId: str | None = None


class DamageRequest(BaseModel):
    userId: str = "dm"
    targetId: str
    amount: int = Field(ge=0)
    damageType: str = "untyped"


class HealingRequest(BaseModel):
    userId: str = "dm"
    targetId: str
    amount: int = Field(ge=0)


class ConditionRequest(BaseModel):
    userId: str = "dm"
    targetId: str
    condition: str


class SpellSlotRequest(BaseModel):
    userId: str = "dm"
    characterId: str
    level: int = Field(ge=1, le=9)
    amount: int = Field(default=1, ge=1)


class ResourceRequest(BaseModel):
    userId: str = "dm"
    characterId: str
    resourceName: str
    amount: int = Field(default=1, ge=1)


class AttackResolveRequest(BaseModel):
    userId: str = "dm"
    attackerId: str
    targetId: str
    attackBonus: int = 0
    damageExpression: str = "1d4"
    damageType: str = "untyped"
    advantage: str = "normal"


class CheckResolveRequest(BaseModel):
    userId: str = "dm"
    actorId: str
    ability: str
    dc: int = Field(ge=0)
    proficient: bool = False
    advantage: str = "normal"


class ReactionWindowRequest(BaseModel):
    userId: str = "dm"
    trigger: str
    actorId: str
    sourceId: str


class ReactionRequest(BaseModel):
    userId: str = "dm"


class PendingActionRequest(BaseModel):
    userId: str = "player-kael"


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
