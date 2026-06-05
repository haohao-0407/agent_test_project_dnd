from __future__ import annotations

from typing import Any

from playscript_agent.api.services import dice_service
from playscript_agent.api.services.game_state import game_state


def start_combat(participant_ids: list[str] | None = None, *, user_id: str) -> dict[str, Any]:
    combat = game_state.start_combat(participant_ids, user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": "Combat started.",
        }
    )
    return combat


def end_combat(*, user_id: str) -> dict[str, Any]:
    combat = game_state.end_combat(user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": "Combat ended.",
        }
    )
    return combat


def end_turn(actor_id: str | None = None, *, user_id: str) -> dict[str, Any]:
    actor_id = actor_id or game_state.current_combat_actor_id()
    combat = game_state.end_turn(actor_id, user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"Turn advanced to {combat['turnState'].get('actorId', 'unknown')}.",
        }
    )
    return combat


def advance_turn(*, user_id: str) -> dict[str, Any]:
    combat = game_state.advance_turn(user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"Turn advanced to {combat['turnState'].get('actorId', 'unknown')}.",
        }
    )
    return combat


def advance_to_player_turn(*, user_id: str) -> dict[str, Any]:
    combat = game_state.snapshot()["combat"]
    if not combat.get("active"):
        raise ValueError("combat is not active")

    max_steps = max(1, len(combat.get("initiativeOrder", [])))
    steps = 0
    while combat.get("active") and steps < max_steps:
        actor_id = game_state.current_combat_actor_id()
        token = _token_for_actor(actor_id)
        if token is None or token.get("kind") == "player":
            break
        game_state.append_event(
            {
                "type": "dm",
                "speaker": "DM",
                "text": f"{token['name']} takes its turn under DM control.",
            }
        )
        combat = game_state.advance_turn(user_id="dm")
        steps += 1

    return combat


def apply_damage(
    target_id: str,
    amount: int,
    *,
    damage_type: str = "untyped",
    user_id: str,
) -> dict[str, Any]:
    result = game_state.apply_damage(
        target_id,
        amount,
        damage_type=damage_type,
        user_id=user_id,
    )
    character = result["character"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} takes {result['amount']} {damage_type} damage.",
        }
    )
    return result


def apply_healing(target_id: str, amount: int, *, user_id: str) -> dict[str, Any]:
    result = game_state.apply_healing(target_id, amount, user_id=user_id)
    character = result["character"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} heals {result['amount']} HP.",
        }
    )
    return result


def apply_condition(target_id: str, condition: str, *, user_id: str) -> dict[str, Any]:
    result = game_state.apply_condition(target_id, condition, user_id=user_id)
    character = result["character"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} gains {result['condition']}.",
        }
    )
    return result


def remove_condition(target_id: str, condition: str, *, user_id: str) -> dict[str, Any]:
    result = game_state.remove_condition(target_id, condition, user_id=user_id)
    character = result["character"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} loses {result['condition']}.",
        }
    )
    return result


def spend_spell_slot(character_id: str, level: int | str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
    result = game_state.spend_spell_slot(character_id, level, amount, user_id=user_id)
    character = result["character"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} spends {result['amount']} level {result['level']} spell slot.",
        }
    )
    return result


def restore_spell_slot(character_id: str, level: int | str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
    result = game_state.restore_spell_slot(character_id, level, amount, user_id=user_id)
    character = result["character"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} restores {result['amount']} level {result['level']} spell slot.",
        }
    )
    return result


def spend_resource(character_id: str, resource_name: str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
    result = game_state.spend_resource(character_id, resource_name, amount, user_id=user_id)
    character = result["character"]
    resource = result["resource"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} spends {result['amount']} {resource['name']}.",
        }
    )
    return result


def restore_resource(character_id: str, resource_name: str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
    result = game_state.restore_resource(character_id, resource_name, amount, user_id=user_id)
    character = result["character"]
    resource = result["resource"]
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{character['name']} restores {result['amount']} {resource['name']}.",
        }
    )
    return result


def resolve_attack(
    attacker_id: str,
    target_id: str,
    *,
    attack_bonus: int,
    damage_expression: str,
    damage_type: str = "untyped",
    advantage: str = "normal",
    user_id: str,
) -> dict[str, Any]:
    game_state.spend_action(attacker_id, "action", user_id=user_id)
    attack_roll = dice_service.roll_and_record(
        _d20_expression(attack_bonus),
        reason="attack roll",
        roller_id=attacker_id,
        advantage=advantage,
    )
    natural_roll = attack_roll["kept"][0]
    target = game_state.find_character(target_id)
    hit = natural_roll == 20 or (natural_roll != 1 and attack_roll["total"] >= int(target["ac"]))
    critical = natural_roll == 20
    damage = None
    if hit:
        damage_roll = dice_service.roll_and_record(
            damage_expression,
            reason="damage roll",
            roller_id=attacker_id,
        )
        amount = damage_roll["total"] * (2 if critical else 1)
        damage = apply_damage(
            target_id,
            amount,
            damage_type=damage_type,
            user_id=user_id,
        )
    result = {
        "attackerId": attacker_id,
        "targetId": target_id,
        "attackRoll": attack_roll,
        "targetAc": target["ac"],
        "hit": hit,
        "critical": critical,
        "damage": damage,
    }
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"{attacker_id} attacks {target_id}: {'hit' if hit else 'miss'}.",
        }
    )
    return result


def resolve_saving_throw(
    actor_id: str,
    *,
    ability: str,
    dc: int,
    advantage: str = "normal",
    user_id: str,
) -> dict[str, Any]:
    if not game_state.can_roll_for_actor(user_id, actor_id):
        raise PermissionError(f"user {user_id} cannot roll for {actor_id}")
    character = game_state.find_character(actor_id)
    modifier = game_state.ability_modifier(character, ability)
    result = dice_service.roll_and_record(
        _d20_expression(modifier),
        reason=f"{ability.upper()} saving throw",
        roller_id=actor_id,
        advantage=advantage,
    )
    return {"actorId": actor_id, "ability": ability.upper(), "dc": dc, "roll": result, "success": result["total"] >= dc}


def resolve_skill_check(
    actor_id: str,
    *,
    ability: str,
    dc: int,
    proficient: bool = False,
    advantage: str = "normal",
    user_id: str,
) -> dict[str, Any]:
    if not game_state.can_roll_for_actor(user_id, actor_id):
        raise PermissionError(f"user {user_id} cannot roll for {actor_id}")
    character = game_state.find_character(actor_id)
    modifier = game_state.ability_modifier(character, ability)
    if proficient:
        modifier += int(character.get("proficiencyBonus", 2))
    result = dice_service.roll_and_record(
        _d20_expression(modifier),
        reason=f"{ability.upper()} skill check",
        roller_id=actor_id,
        advantage=advantage,
    )
    return {"actorId": actor_id, "ability": ability.upper(), "dc": dc, "roll": result, "success": result["total"] >= dc}


def open_reaction_window(
    trigger: str,
    actor_id: str,
    source_id: str,
    *,
    user_id: str,
) -> dict[str, Any]:
    window = game_state.open_reaction_window(
        trigger=trigger,
        actor_id=actor_id,
        source_id=source_id,
        user_id=user_id,
    )
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Combat",
            "text": f"Reaction window opened for {actor_id}.",
        }
    )
    return window


def resolve_reaction(window_id: str, *, user_id: str) -> dict[str, Any]:
    return game_state.resolve_reaction(window_id, "opportunity_attack", user_id=user_id)


def decline_reaction(window_id: str, *, user_id: str) -> dict[str, Any]:
    return game_state.decline_reaction(window_id, user_id=user_id)


def _d20_expression(modifier: int) -> str:
    if modifier == 0:
        return "1d20"
    sign = "+" if modifier > 0 else ""
    return f"1d20{sign}{modifier}"


def _token_for_actor(actor_id: str) -> dict[str, Any] | None:
    state = game_state.snapshot()
    normalized = actor_id.strip().lower()
    for token in state["tokens"]:
        if str(token.get("actorId", token["id"])).strip().lower() == normalized:
            return token
    return None
