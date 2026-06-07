from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from playscript_agent.api.dependencies import get_principal
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
from playscript_agent.api.services import adventure_service, chat_service, combat_service
from playscript_agent.api.services.game_state import Principal, get_store


router = APIRouter()


def _raise_http(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


@router.post("/api/combat/start")
def start_combat(request: CombatStartRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        if request.sceneId:
            adventure_service.prepare_combat_scene(
                session_id=principal.session_id,
                scene_id=request.sceneId,
                user_id=principal.user_id,
            )
        combat = combat_service.start_combat(request.participantIds, user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": store.snapshot()}


@router.post("/api/combat/end")
def end_combat(request: CombatStartRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        combat = combat_service.end_combat(user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": store.snapshot()}


@router.post("/api/combat/end-turn")
def end_turn(request: CombatTurnRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        combat = combat_service.end_turn(request.actorId, user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": store.snapshot()}


@router.post("/api/combat/advance-turn")
def advance_turn(request: CombatTurnRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        combat = combat_service.advance_turn(user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": store.snapshot()}


@router.post("/api/combat/advance-to-player-turn")
def advance_to_player_turn(request: CombatTurnRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        combat = chat_service.advance_to_player_turn(user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"combat": combat, "state": store.snapshot()}


@router.post("/api/combat/apply-damage")
def apply_damage(request: DamageRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.apply_damage(
            request.targetId,
            request.amount,
            damage_type=request.damageType,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/apply-healing")
def apply_healing(request: HealingRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.apply_healing(
            request.targetId,
            request.amount,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/apply-condition")
def apply_condition(request: ConditionRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.apply_condition(
            request.targetId,
            request.condition,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/remove-condition")
def remove_condition(request: ConditionRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.remove_condition(
            request.targetId,
            request.condition,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/spend-spell-slot")
def spend_spell_slot(request: SpellSlotRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.spend_spell_slot(
            request.characterId,
            request.level,
            request.amount,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/restore-spell-slot")
def restore_spell_slot(request: SpellSlotRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.restore_spell_slot(
            request.characterId,
            request.level,
            request.amount,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/spend-resource")
def spend_resource(request: ResourceRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.spend_resource(
            request.characterId,
            request.resourceName,
            request.amount,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/restore-resource")
def restore_resource(request: ResourceRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.restore_resource(
            request.characterId,
            request.resourceName,
            request.amount,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/resolve-attack")
def resolve_attack(request: AttackResolveRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.resolve_attack(
            request.attackerId,
            request.targetId,
            attack_bonus=request.attackBonus,
            damage_expression=request.damageExpression,
            damage_type=request.damageType,
            advantage=request.advantage,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/resolve-saving-throw")
def resolve_saving_throw(request: CheckResolveRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.resolve_saving_throw(
            request.actorId,
            ability=request.ability,
            dc=request.dc,
            advantage=request.advantage,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/resolve-skill-check")
def resolve_skill_check(request: CheckResolveRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        result = combat_service.resolve_skill_check(
            request.actorId,
            ability=request.ability,
            dc=request.dc,
            proficient=request.proficient,
            advantage=request.advantage,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"result": result, "state": store.snapshot()}


@router.post("/api/combat/reactions/open")
def open_reaction_window(request: ReactionWindowRequest, principal: Principal = Depends(get_principal)) -> dict:
    store = get_store(principal.session_id)
    try:
        reaction_window = combat_service.open_reaction_window(
            request.trigger,
            request.actorId,
            request.sourceId,
            user_id=principal.user_id,
        )
    except Exception as error:
        _raise_http(error)
    return {"reactionWindow": reaction_window, "state": store.snapshot()}


@router.post("/api/combat/reactions/{window_id}/resolve")
def resolve_reaction(
    window_id: str,
    request: ReactionRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    store = get_store(principal.session_id)
    try:
        reaction_window = combat_service.resolve_reaction(window_id, user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"reactionWindow": reaction_window, "state": store.snapshot()}


@router.post("/api/combat/reactions/{window_id}/decline")
def decline_reaction(
    window_id: str,
    request: ReactionRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    store = get_store(principal.session_id)
    try:
        reaction_window = combat_service.decline_reaction(window_id, user_id=principal.user_id)
    except Exception as error:
        _raise_http(error)
    return {"reactionWindow": reaction_window, "state": store.snapshot()}
