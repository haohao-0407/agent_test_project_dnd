from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import (
    AttackResolveRequest,
    CheckResolveRequest,
    CombatStartRequest,
    CombatTurnRequest,
    ConditionRequest,
    DamageRequest,
    HealingRequest,
    ReactionRequest,
    ReactionWindowRequest,
    ResourceRequest,
    SpellSlotRequest,
)
from playscript_agent.api.services import combat_service
from playscript_agent.api.services.game_state import game_state


router = APIRouter()


def _raise_http(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


@router.post("/api/combat/start")
def start_combat(request: CombatStartRequest) -> dict:
    try:
        combat = combat_service.start_combat(request.participantIds, user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": game_state.snapshot()}


@router.post("/api/combat/end")
def end_combat(request: CombatStartRequest) -> dict:
    try:
        combat = combat_service.end_combat(user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": game_state.snapshot()}


@router.post("/api/combat/end-turn")
def end_turn(request: CombatTurnRequest) -> dict:
    try:
        combat = combat_service.end_turn(request.actorId, user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": game_state.snapshot()}


@router.post("/api/combat/advance-turn")
def advance_turn(request: CombatTurnRequest) -> dict:
    try:
        combat = combat_service.advance_turn(user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": game_state.snapshot()}


@router.post("/api/combat/advance-to-player-turn")
def advance_to_player_turn(request: CombatTurnRequest) -> dict:
    try:
        combat = combat_service.advance_to_player_turn(user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": game_state.snapshot()}


@router.post("/api/combat/apply-damage")
def apply_damage(request: DamageRequest) -> dict:
    try:
        result = combat_service.apply_damage(
            request.targetId,
            request.amount,
            damage_type=request.damageType,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/apply-healing")
def apply_healing(request: HealingRequest) -> dict:
    try:
        result = combat_service.apply_healing(
            request.targetId,
            request.amount,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/apply-condition")
def apply_condition(request: ConditionRequest) -> dict:
    try:
        result = combat_service.apply_condition(
            request.targetId,
            request.condition,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/remove-condition")
def remove_condition(request: ConditionRequest) -> dict:
    try:
        result = combat_service.remove_condition(
            request.targetId,
            request.condition,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/spend-spell-slot")
def spend_spell_slot(request: SpellSlotRequest) -> dict:
    try:
        result = combat_service.spend_spell_slot(
            request.characterId,
            request.level,
            request.amount,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/restore-spell-slot")
def restore_spell_slot(request: SpellSlotRequest) -> dict:
    try:
        result = combat_service.restore_spell_slot(
            request.characterId,
            request.level,
            request.amount,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/spend-resource")
def spend_resource(request: ResourceRequest) -> dict:
    try:
        result = combat_service.spend_resource(
            request.characterId,
            request.resourceName,
            request.amount,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/restore-resource")
def restore_resource(request: ResourceRequest) -> dict:
    try:
        result = combat_service.restore_resource(
            request.characterId,
            request.resourceName,
            request.amount,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/resolve-attack")
def resolve_attack(request: AttackResolveRequest) -> dict:
    try:
        result = combat_service.resolve_attack(
            request.attackerId,
            request.targetId,
            attack_bonus=request.attackBonus,
            damage_expression=request.damageExpression,
            damage_type=request.damageType,
            advantage=request.advantage,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/resolve-saving-throw")
def resolve_saving_throw(request: CheckResolveRequest) -> dict:
    try:
        result = combat_service.resolve_saving_throw(
            request.actorId,
            ability=request.ability,
            dc=request.dc,
            advantage=request.advantage,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/resolve-skill-check")
def resolve_skill_check(request: CheckResolveRequest) -> dict:
    try:
        result = combat_service.resolve_skill_check(
            request.actorId,
            ability=request.ability,
            dc=request.dc,
            proficient=request.proficient,
            advantage=request.advantage,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": game_state.snapshot()}


@router.post("/api/combat/reactions/open")
def open_reaction_window(request: ReactionWindowRequest) -> dict:
    try:
        reaction_window = combat_service.open_reaction_window(
            request.trigger,
            request.actorId,
            request.sourceId,
            user_id=request.userId,
        )
    except Exception as error:
        _raise_http(error)
    return {"reactionWindow": reaction_window, "state": game_state.snapshot()}


@router.post("/api/combat/reactions/{window_id}/resolve")
def resolve_reaction(window_id: str, request: ReactionRequest) -> dict:
    try:
        reaction_window = combat_service.resolve_reaction(window_id, user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"reactionWindow": reaction_window, "state": game_state.snapshot()}


@router.post("/api/combat/reactions/{window_id}/decline")
def decline_reaction(window_id: str, request: ReactionRequest) -> dict:
    try:
        reaction_window = combat_service.decline_reaction(window_id, user_id=request.userId)
    except Exception as error:
        _raise_http(error)
    return {"reactionWindow": reaction_window, "state": game_state.snapshot()}
