from __future__ import annotations

from pydantic import BaseModel, Field


class JoinRequest(BaseModel):
    role: str = "player"
    username: str = Field(min_length=1, max_length=40)


class DiceRequest(BaseModel):
    expression: str = "1d20"
    reason: str = "manual roll"
    rollerId: str | None = None
    advantage: str = "normal"


class TokenMoveRequest(BaseModel):
    tokenId: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class MapUpdateRequest(BaseModel):
    updates: dict = Field(default_factory=dict)


class MapLayerUpdateRequest(BaseModel):
    layer: str
    items: list[dict] = Field(default_factory=list)


class MapBackgroundUpdateRequest(BaseModel):
    background: dict = Field(default_factory=dict)


class CombatStartRequest(BaseModel):
    participantIds: list[str] | None = None
    sceneId: str | None = None


class CombatTurnRequest(BaseModel):
    actorId: str | None = None


class DamageRequest(BaseModel):
    targetId: str
    amount: int = Field(ge=0)
    damageType: str = "untyped"


class HealingRequest(BaseModel):
    targetId: str
    amount: int = Field(ge=0)


class ConditionRequest(BaseModel):
    targetId: str
    condition: str


class SpellSlotRequest(BaseModel):
    characterId: str
    level: int = Field(ge=1, le=9)
    amount: int = Field(default=1, ge=1)


class ResourceRequest(BaseModel):
    characterId: str
    resourceName: str
    amount: int = Field(default=1, ge=1)


class AttackResolveRequest(BaseModel):
    attackerId: str
    targetId: str
    attackBonus: int = 0
    damageExpression: str = "1d4"
    damageType: str = "untyped"
    advantage: str = "normal"


class CheckResolveRequest(BaseModel):
    actorId: str
    ability: str
    dc: int = Field(ge=0)
    proficient: bool = False
    advantage: str = "normal"


class ReactionWindowRequest(BaseModel):
    trigger: str
    actorId: str
    sourceId: str


class ReactionRequest(BaseModel):
    pass


class PendingActionRequest(BaseModel):
    pass


class ChatRequest(BaseModel):
    message: str
    speaker: str = "player"


class AdventureStartRequest(BaseModel):
    moduleName: str = "凡戴尔的失落矿坑"


class AdventureReadyRequest(BaseModel):
    ready: bool = True
    moduleName: str = "凡戴尔的失落矿坑"


class AdventureSceneJumpRequest(BaseModel):
    moduleName: str = "凡戴尔的失落矿坑"
    sceneId: str


class CharacterUpdateRequest(BaseModel):
    updates: dict = Field(default_factory=dict)


class CharacterCreateRequest(BaseModel):
    character: dict = Field(default_factory=dict)


class MonsterUpdateRequest(BaseModel):
    updates: dict = Field(default_factory=dict)


class MonsterCreateRequest(BaseModel):
    monster: dict = Field(default_factory=dict)


class RagQueryRequest(BaseModel):
    query: str
    k: int = Field(default=4, ge=1, le=12)
