from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from playscript_agent.api.services import combat_service, dice_service, map_service
from playscript_agent.api.services.game_state import game_state
from playscript_agent.llm import get_llm


ToolName = str


class ToolCall(TypedDict):
    name: ToolName
    arguments: dict[str, Any]


class DmPlan(TypedDict):
    tool_calls: list[ToolCall]
    content: str
    source: Literal["llm", "fallback"]
    rule_context: str


DM_TOOL_SCHEMAS = [
    {
        "name": "move_token",
        "description": "Move a token on the battle map. Use this for any player or DM intent that changes a token position.",
        "parameters": {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Token id, such as kael, mira, goblin-1, or wolf-1.",
                },
                "x": {
                    "type": "integer",
                    "description": "0-based grid x coordinate. Do not convert or subtract from player-provided coordinates.",
                },
                "y": {
                    "type": "integer",
                    "description": "0-based grid y coordinate. Do not convert or subtract from player-provided coordinates.",
                },
            },
            "required": ["token_id", "x", "y"],
        },
    },
    {
        "name": "roll_dice",
        "description": "Roll dice for DND checks, attacks, saves, damage, or any explicit dice expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Dice expression such as 1d20+5, 2d6+3, or 1d8.",
                },
                "reason": {
                    "type": "string",
                    "description": "Short reason, such as attack roll, ability check, or chat roll.",
                },
                "roller_id": {
                    "type": "string",
                    "description": "The speaker or character that requested the roll.",
                },
                "advantage": {
                    "type": "string",
                    "enum": ["normal", "advantage", "disadvantage"],
                    "description": "DND d20 advantage mode.",
                },
            },
            "required": ["expression", "reason"],
        },
    },
]

DM_TOOL_SCHEMAS.extend(
    [
        {
            "name": "start_combat",
            "description": "Start DND 5e combat and roll initiative for the given participants, or all map tokens if omitted. DM-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "participant_ids": {"type": "array", "items": {"type": "string"}},
                    "scene_id": {"type": "string", "description": "Optional combat scene id from the current module scene collection."},
                },
            },
        },
        {
            "name": "end_combat",
            "description": "End tactical combat and return the session to exploration mode when the encounter is resolved. DM-only.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "switch_exploration_scene",
            "description": "Switch to another exploration scene from the current module without entering tactical combat. DM-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "Exploration scene id from the module scene collection."},
                    "module_name": {"type": "string", "description": "Optional module name. Defaults to the active adventure module."},
                },
                "required": ["scene_id"],
            },
        },
        {
            "name": "end_turn",
            "description": "End the current combat actor's turn and advance initiative.",
            "parameters": {
                "type": "object",
                "properties": {"actor_id": {"type": "string"}},
            },
        },
        {
            "name": "advance_turn",
            "description": "Force initiative to advance. DM-only.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "apply_damage",
            "description": "Apply deterministic damage to an actor or character.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "amount": {"type": "integer"},
                    "damage_type": {"type": "string"},
                },
                "required": ["target_id", "amount"],
            },
        },
        {
            "name": "apply_healing",
            "description": "Apply healing to an actor or character.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "amount": {"type": "integer"},
                },
                "required": ["target_id", "amount"],
            },
        },
        {
            "name": "apply_condition",
            "description": "Apply a supported 5e condition to an actor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "condition": {"type": "string"},
                },
                "required": ["target_id", "condition"],
            },
        },
        {
            "name": "remove_condition",
            "description": "Remove a condition from an actor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "condition": {"type": "string"},
                },
                "required": ["target_id", "condition"],
            },
        },
        {
            "name": "spend_spell_slot",
            "description": "Spend one or more spell slots for a character. Use this instead of directly editing spellcasting state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "level": {"type": "integer", "minimum": 1, "maximum": 9},
                    "amount": {"type": "integer", "minimum": 1},
                },
                "required": ["character_id", "level"],
            },
        },
        {
            "name": "restore_spell_slot",
            "description": "Restore one or more spell slots for a character, clamped to the slot maximum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "level": {"type": "integer", "minimum": 1, "maximum": 9},
                    "amount": {"type": "integer", "minimum": 1},
                },
                "required": ["character_id", "level"],
            },
        },
        {
            "name": "spend_resource",
            "description": "Spend a named limited-use character resource, such as Second Wind or Arcane Recovery.",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "resource_name": {"type": "string"},
                    "amount": {"type": "integer", "minimum": 1},
                },
                "required": ["character_id", "resource_name"],
            },
        },
        {
            "name": "restore_resource",
            "description": "Restore a named limited-use character resource, clamped to the resource maximum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "resource_name": {"type": "string"},
                    "amount": {"type": "integer", "minimum": 1},
                },
                "required": ["character_id", "resource_name"],
            },
        },
        {
            "name": "restore_action_economy",
            "description": "Restore a combat action economy slot or movement for the current turn, such as Action Surge, Haste, regaining a reaction, or refunded movement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "actor_id": {"type": "string"},
                    "action_type": {
                        "type": "string",
                        "enum": ["action", "bonus_action", "reaction", "object_interaction", "movement", "all"],
                    },
                    "amount": {"type": "integer", "minimum": 0, "description": "Movement feet to restore when action_type is movement. 0 restores all spent movement."},
                    "reason": {"type": "string", "description": "Short rules reason, such as Action Surge, Haste, or reaction refresh."},
                },
                "required": ["actor_id", "action_type"],
            },
        },
        {
            "name": "resolve_attack",
            "description": "Resolve a 5e attack roll, spend the attacker's action, and apply damage on hit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attacker_id": {"type": "string"},
                    "target_id": {"type": "string"},
                    "attack_bonus": {"type": "integer"},
                    "damage_expression": {"type": "string"},
                    "damage_type": {"type": "string"},
                    "advantage": {"type": "string", "enum": ["normal", "advantage", "disadvantage"]},
                },
                "required": ["attacker_id", "target_id", "attack_bonus", "damage_expression"],
            },
        },
        {
            "name": "resolve_saving_throw",
            "description": "Roll and resolve an ability saving throw against a DC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "actor_id": {"type": "string"},
                    "ability": {"type": "string"},
                    "dc": {"type": "integer"},
                    "advantage": {"type": "string", "enum": ["normal", "advantage", "disadvantage"]},
                },
                "required": ["actor_id", "ability", "dc"],
            },
        },
        {
            "name": "resolve_skill_check",
            "description": "Roll and resolve an ability or skill check against a DC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "actor_id": {"type": "string"},
                    "ability": {"type": "string"},
                    "dc": {"type": "integer"},
                    "proficient": {"type": "boolean"},
                    "advantage": {"type": "string", "enum": ["normal", "advantage", "disadvantage"]},
                },
                "required": ["actor_id", "ability", "dc"],
            },
        },
        {
            "name": "open_reaction_window",
            "description": "Open a deterministic reaction window, such as an opportunity attack trigger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string"},
                    "actor_id": {"type": "string"},
                    "source_id": {"type": "string"},
                },
                "required": ["trigger", "actor_id", "source_id"],
            },
        },
        {
            "name": "resolve_reaction",
            "description": "Resolve an open reaction window.",
            "parameters": {
                "type": "object",
                "properties": {"window_id": {"type": "string"}},
                "required": ["window_id"],
            },
        },
        {
            "name": "decline_reaction",
            "description": "Decline an open reaction window.",
            "parameters": {
                "type": "object",
                "properties": {"window_id": {"type": "string"}},
                "required": ["window_id"],
            },
        },
        {
            "name": "edit_map_layer",
            "description": "Replace one structured map layer such as terrain, walls, doors, fog, annotations, effects, or dmNotes. DM-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "layer": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["layer", "items"],
            },
        },
        {
            "name": "set_map_background",
            "description": "Set the map background image metadata. DM-only.",
            "parameters": {
                "type": "object",
                "properties": {"background": {"type": "object"}},
                "required": ["background"],
            },
        },
    ]
)

DM_SYSTEM_PROMPT = """You are the Dungeon Master for a DND tabletop web app.
Use tool calls for every action that changes game state, moves tokens, rolls dice, or changes HP, conditions, spell slots, or resources.
Do not reveal tool JSON, function names, or backend details in player-facing text.
If no tool is needed, answer in concise Chinese as the DM.
Exploration and combat are separate modes. In exploration mode, do not move tokens on the grid; narrate scenes, NPC dialogue, choices, and checks like a visual novel.
Only call start_combat when the module scene, player choices, or failed checks make a fight begin. Once combat starts, the app switches to the tactical grid and combat tools.
Call switch_exploration_scene when the party clearly moves to another module exploration scene, location, or chapter without entering combat.
Call end_combat when the fight is resolved, enemies are defeated, surrender, flee, or the scene clearly returns to exploration.
For map coordinates, every surface uses 0-based x/y: player text, tool arguments, tool results, current_state, events, and system messages.
Never convert, add, or subtract coordinate values.
Keep public replies short and based only on the known game state and tool results.
The current_state JSON is authoritative for player character facts. Never invent or infer a player character's class, race, HP, AC, skills, resources, spell slots, equipment, or conditions. If a fact is missing, say it is unknown."""


MOVE_PATTERNS = [
    re.compile(
        r"\bmove\s+(?P<token>[a-zA-Z0-9_-]+)\s+(?:to\s*)?"
        r"\(?(?P<x>\d+)\s*[, ]\s*(?P<y>\d+)\)?",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?P<token>[a-zA-Z0-9_-]+|凯尔|米拉|地精|座狼)"
        r".*?(?:移动|移動|move).*?(?:到|to)?\s*"
        r"\(?(?P<x>\d+)\s*[,， ]\s*(?P<y>\d+)\)?",
        flags=re.IGNORECASE,
    ),
]

TOKEN_ALIASES = {
    "凯尔": "kael",
    "米拉": "mira",
    "地精": "goblin-1",
    "座狼": "wolf-1",
    "goblin": "goblin-1",
    "wolf": "wolf-1",
}

MONSTER_TURN_PROMPT = """It is the current monster's turn in tactical combat.
Control only that monster for this turn. Choose sensible DND 5e actions from current_state.
Prefer resolve_attack when a player character is a plausible target; otherwise move the monster or use another legal combat tool.
Do not start or end combat from a monster turn.
Always finish the monster turn with end_turn for the current monster."""

MONSTER_TURN_TOOLS = {
    "move_token",
    "roll_dice",
    "end_turn",
    "apply_damage",
    "apply_healing",
    "apply_condition",
    "remove_condition",
    "spend_resource",
    "restore_resource",
    "restore_action_economy",
    "resolve_attack",
    "resolve_saving_throw",
    "resolve_skill_check",
    "open_reaction_window",
    "resolve_reaction",
    "decline_reaction",
}

ATTACK_PATTERN = re.compile(
    r"(?P<name>.*?)\s+(?P<bonus>[+-]\d+)\s+(?P<damage>\d+d\d+(?:[+-]\d+)?)",
    flags=re.IGNORECASE,
)


def handle_chat(
    message: str,
    *,
    speaker: str = "player",
    user_id: str = "player-kael",
) -> dict[str, Any]:
    message = message.strip()
    if not message:
        raise ValueError("message is required")

    game_state.append_event({"type": "player", "speaker": speaker, "text": message})

    dm_plan = plan_dm_turn(message, speaker=speaker, user_id=user_id)
    tool_calls = dm_plan["tool_calls"]
    tool_results = [
        execute_tool_call(tool_call, user_id=user_id) for tool_call in tool_calls
    ]
    dm_text = narrate_dm_response(
        message,
        speaker=speaker,
        user_id=user_id,
        tool_results=tool_results,
        planned_content=dm_plan["content"],
        rule_context=dm_plan["rule_context"],
    )
    game_state.append_event(
        {
            "type": "dm",
            "speaker": "DM",
            "text": dm_text,
        }
    )
    snapshot = game_state.snapshot()
    return {
        "toolCalls": tool_calls,
        "toolResults": tool_results,
        "dmSource": dm_plan["source"],
        "pendingActions": snapshot.get("pendingActions", []),
        "state": snapshot,
    }


def advance_to_player_turn(*, user_id: str) -> dict[str, Any]:
    return combat_service.advance_to_player_turn(
        user_id=user_id,
        monster_turn_runner=_run_monster_agent_turn,
    )


def _run_monster_agent_turn(actor_id: str) -> None:
    token = _token_for_actor(actor_id)
    actor_name = token.get("name", actor_id) if token else actor_id
    game_state.append_event(
        {
            "type": "dm",
            "speaker": "DM",
            "text": f"{actor_name} 开始由 DM agent 执行回合。",
        }
    )
    dm_plan = _plan_monster_turn(actor_id)
    tool_results: list[dict[str, Any]] = []
    for tool_call in dm_plan["tool_calls"]:
        if not _is_current_actor_turn(actor_id):
            break
        tool_results.append(execute_tool_call(tool_call, user_id="dm"))

    if _is_current_actor_turn(actor_id):
        tool_results.append(
            execute_tool_call(
                {"name": "end_turn", "arguments": {"actor_id": actor_id}},
                user_id="dm",
            )
        )

    dm_text = dm_plan["content"].strip() or build_result_message(tool_results)
    game_state.append_event(
        {
            "type": "dm",
            "speaker": "DM",
            "text": dm_text,
        }
    )


def _plan_monster_turn(actor_id: str) -> DmPlan:
    try:
        rule_context = _build_rule_context(f"{actor_id} monster combat turn", user_id="dm")
        llm = get_llm("dm")
        tool_bound_llm = llm.bind_tools(DM_TOOL_SCHEMAS)
        response = tool_bound_llm.invoke(
            _build_monster_turn_messages(
                actor_id,
                rule_context=rule_context,
            )
        )
        tool_calls = _filter_monster_turn_tool_calls(
            _extract_tool_calls(response, user_id="dm"),
            actor_id=actor_id,
        )
        if not tool_calls:
            tool_calls = _fallback_monster_turn_tool_calls(actor_id)
        return {
            "tool_calls": tool_calls,
            "content": _extract_content(response),
            "source": "llm",
            "rule_context": rule_context,
        }
    except Exception:
        return {
            "tool_calls": _fallback_monster_turn_tool_calls(actor_id),
            "content": "",
            "source": "fallback",
            "rule_context": "",
        }


def _build_monster_turn_messages(actor_id: str, *, rule_context: str = "") -> list[tuple[str, str]]:
    messages = [
        ("system", DM_SYSTEM_PROMPT),
        ("system", MONSTER_TURN_PROMPT),
        ("system", _build_state_context(user_id="dm")),
    ]
    if rule_context:
        messages.append(("system", rule_context))
    messages.append(
        (
            "human",
            f"Current monster actor_id: {actor_id}\nResolve this monster turn with tool calls.",
        )
    )
    return messages


def plan_dm_turn(message: str, *, speaker: str, user_id: str = "player-kael") -> DmPlan:
    llm_plan = _plan_with_llm(message, speaker=speaker, user_id=user_id)
    if llm_plan is not None:
        return llm_plan
    return {
        "tool_calls": _fallback_plan_tool_calls(message, speaker=speaker, user_id=user_id),
        "content": "",
        "source": "fallback",
        "rule_context": "",
    }


def plan_tool_calls(
    message: str,
    *,
    speaker: str,
    user_id: str = "player-kael",
) -> list[ToolCall]:
    return plan_dm_turn(message, speaker=speaker, user_id=user_id)["tool_calls"]


def _fallback_plan_tool_calls(
    message: str,
    *,
    speaker: str,
    user_id: str,
) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    if _can_use_tactical_grid():
        move_call = _plan_move_call(message)
        if move_call:
            tool_calls.append(move_call)

    roll_call = _plan_roll_call(message, speaker=speaker, user_id=user_id)
    if roll_call:
        tool_calls.append(roll_call)

    return tool_calls


def _plan_with_llm(message: str, *, speaker: str, user_id: str) -> DmPlan | None:
    try:
        rule_context = _build_rule_context(message, user_id=user_id)
        llm = get_llm("dm")
        tool_bound_llm = llm.bind_tools(DM_TOOL_SCHEMAS)
        response = tool_bound_llm.invoke(
            _build_dm_messages(
                message,
                speaker=speaker,
                user_id=user_id,
                rule_context=rule_context,
            )
        )
    except Exception:
        return None

    return {
        "tool_calls": _extract_tool_calls(response, user_id=user_id),
        "content": _extract_content(response),
        "source": "llm",
        "rule_context": rule_context,
    }


def execute_tool_call(tool_call: ToolCall, *, user_id: str | None = None) -> dict[str, Any]:
    name = tool_call["name"]
    arguments = tool_call["arguments"]
    authority_user_id = _authority_user_for_tool(name, user_id)
    if name == "move_token":
        token = map_service.move_token(
            str(arguments["token_id"]),
            int(arguments["x"]),
            int(arguments["y"]),
            user_id=user_id,
        )
        return {"name": name, "result": {"token": token}}
    if name == "roll_dice":
        roller_id = _safe_roller_id(arguments.get("roller_id"), user_id=user_id)
        result = dice_service.roll_and_record(
            str(arguments["expression"]),
            reason=str(arguments.get("reason", "chat roll")),
            roller_id=roller_id,
            advantage=str(arguments.get("advantage", "normal")),
        )
        return {"name": name, "result": result}
    if name == "start_combat":
        scene_id = arguments.get("scene_id")
        if scene_id:
            from playscript_agent.api.services import adventure_service

            adventure_service.prepare_combat_scene(scene_id=str(scene_id), user_id=authority_user_id)
        combat = combat_service.start_combat(
            arguments.get("participant_ids"),
            user_id=authority_user_id,
        )
        return {"name": name, "result": {"combat": combat}}
    if name == "end_combat":
        combat = combat_service.end_combat(user_id=authority_user_id)
        return {"name": name, "result": {"combat": combat}}
    if name == "switch_exploration_scene":
        from playscript_agent.api.services import adventure_service

        state = game_state.snapshot()
        adventure = state.get("adventure", {})
        module_name = str(arguments.get("module_name") or adventure.get("moduleName") or "凡戴尔的失落矿坑")
        scene_state = adventure_service.switch_exploration_scene(
            user_id=authority_user_id,
            module_name=module_name,
            scene_id=str(arguments["scene_id"]),
        )
        return {"name": name, "result": {"state": scene_state}}
    if name == "end_turn":
        combat = combat_service.end_turn(
            arguments.get("actor_id"),
            user_id=user_id or "dm",
        )
        return {"name": name, "result": {"combat": combat}}
    if name == "advance_turn":
        combat = combat_service.advance_turn(user_id=authority_user_id)
        return {"name": name, "result": {"combat": combat}}
    if name == "apply_damage":
        result = combat_service.apply_damage(
            str(arguments["target_id"]),
            int(arguments["amount"]),
            damage_type=str(arguments.get("damage_type", "untyped")),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "apply_healing":
        result = combat_service.apply_healing(
            str(arguments["target_id"]),
            int(arguments["amount"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "apply_condition":
        result = combat_service.apply_condition(
            str(arguments["target_id"]),
            str(arguments["condition"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "remove_condition":
        result = combat_service.remove_condition(
            str(arguments["target_id"]),
            str(arguments["condition"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "spend_spell_slot":
        result = combat_service.spend_spell_slot(
            _canonical_token(str(arguments["character_id"])),
            arguments["level"],
            int(arguments.get("amount", 1)),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "restore_spell_slot":
        result = combat_service.restore_spell_slot(
            _canonical_token(str(arguments["character_id"])),
            arguments["level"],
            int(arguments.get("amount", 1)),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "spend_resource":
        result = combat_service.spend_resource(
            _canonical_token(str(arguments["character_id"])),
            str(arguments["resource_name"]),
            int(arguments.get("amount", 1)),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "restore_resource":
        result = combat_service.restore_resource(
            _canonical_token(str(arguments["character_id"])),
            str(arguments["resource_name"]),
            int(arguments.get("amount", 1)),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "restore_action_economy":
        result = combat_service.restore_action_economy(
            _canonical_token(str(arguments["actor_id"])),
            str(arguments["action_type"]),
            amount=int(arguments.get("amount", 0)),
            reason=str(arguments.get("reason", "action recovery")),
            user_id=authority_user_id,
        )
        return {"name": name, "result": result}
    if name == "resolve_attack":
        result = combat_service.resolve_attack(
            str(arguments["attacker_id"]),
            str(arguments["target_id"]),
            attack_bonus=int(arguments.get("attack_bonus", 0)),
            damage_expression=str(arguments.get("damage_expression", "1d4")),
            damage_type=str(arguments.get("damage_type", "untyped")),
            advantage=str(arguments.get("advantage", "normal")),
            user_id=user_id or "dm",
        )
        return {"name": name, "result": result}
    if name == "resolve_saving_throw":
        result = combat_service.resolve_saving_throw(
            str(arguments["actor_id"]),
            ability=str(arguments["ability"]),
            dc=int(arguments["dc"]),
            advantage=str(arguments.get("advantage", "normal")),
            user_id=user_id or "dm",
        )
        return {"name": name, "result": result}
    if name == "resolve_skill_check":
        result = combat_service.resolve_skill_check(
            str(arguments["actor_id"]),
            ability=str(arguments["ability"]),
            dc=int(arguments["dc"]),
            proficient=bool(arguments.get("proficient", False)),
            advantage=str(arguments.get("advantage", "normal")),
            user_id=user_id or "dm",
        )
        return {"name": name, "result": result}
    if name == "open_reaction_window":
        result = combat_service.open_reaction_window(
            str(arguments["trigger"]),
            str(arguments["actor_id"]),
            str(arguments["source_id"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": {"reactionWindow": result}}
    if name == "resolve_reaction":
        result = combat_service.resolve_reaction(
            str(arguments["window_id"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": {"reactionWindow": result}}
    if name == "decline_reaction":
        result = combat_service.decline_reaction(
            str(arguments["window_id"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": {"reactionWindow": result}}
    if name == "edit_map_layer":
        game_map = map_service.edit_map_layer(
            str(arguments["layer"]),
            list(arguments.get("items", [])),
            user_id=authority_user_id,
        )
        return {"name": name, "result": {"map": game_map}}
    if name == "set_map_background":
        game_map = map_service.set_map_background(
            dict(arguments["background"]),
            user_id=authority_user_id,
        )
        return {"name": name, "result": {"map": game_map}}
    raise ValueError(f"unsupported tool call: {name}")


DM_AUTHORITY_TOOLS = {
    "start_combat",
    "end_combat",
    "switch_exploration_scene",
    "advance_turn",
    "apply_damage",
    "apply_healing",
    "apply_condition",
    "remove_condition",
    "spend_spell_slot",
    "restore_spell_slot",
    "spend_resource",
    "restore_resource",
    "restore_action_economy",
    "open_reaction_window",
    "resolve_reaction",
    "decline_reaction",
    "edit_map_layer",
    "set_map_background",
}


def _authority_user_for_tool(name: str, user_id: str | None) -> str:
    if name in DM_AUTHORITY_TOOLS:
        return "dm"
    return user_id or "dm"


def narrate_dm_response(
    message: str,
    *,
    speaker: str,
    user_id: str,
    tool_results: list[dict[str, Any]],
    planned_content: str,
    rule_context: str = "",
) -> str:
    fallback = build_result_message(tool_results) if tool_results else planned_content.strip()
    if not fallback:
        fallback = build_result_message([])
    if not tool_results:
        return fallback

    try:
        llm = get_llm("dm")
        response = llm.invoke(
            _build_narration_messages(
                message,
                speaker=speaker,
                user_id=user_id,
                tool_results=tool_results,
                rule_context=rule_context,
            )
        )
    except Exception:
        return fallback

    content = _extract_content(response)
    return content or fallback


def _build_narration_messages(
    message: str,
    *,
    speaker: str,
    user_id: str,
    tool_results: list[dict[str, Any]],
    rule_context: str,
) -> list[tuple[str, str]]:
    messages = [
        ("system", DM_SYSTEM_PROMPT),
        ("system", _build_state_context(user_id=user_id)),
    ]
    if rule_context:
        messages.append(("system", rule_context))
    messages.extend(
        [
            (
                "system",
                "Write one concise Chinese DM reply using only current_state, "
                "retrieved rule context, and tool results. Do not mention JSON, "
                "function calls, tools, or hidden backend details.",
            ),
            (
                "human",
                "Speaker: "
                f"{speaker}\nPlayer action: {message}\n"
                f"Tool results: {json.dumps(tool_results, ensure_ascii=False)}",
            ),
        ]
    )
    return messages


def build_result_message(tool_results: list[dict[str, Any]]) -> str:
    if not tool_results:
        return "行动已记录。"

    parts: list[str] = []
    for tool_result in tool_results:
        if tool_result["name"] == "move_token":
            token = tool_result["result"]["token"]
            parts.append(f"{token['name']} 移动到 ({token['x']}, {token['y']})")
        elif tool_result["name"] == "roll_dice":
            result = tool_result["result"]
            parts.append(f"{result['expression']} 结果为 {result['total']}")
        elif tool_result["name"] == "end_combat":
            parts.append("战斗结束，场景回到探索")
        elif tool_result["name"] == "switch_exploration_scene":
            adventure = tool_result["result"]["state"].get("adventure", {})
            scene_name = adventure.get("scene") or adventure.get("explorationSceneId") or "新场景"
            parts.append(f"场景切换到 {scene_name}")
        elif tool_result["name"] == "end_turn":
            combat = tool_result["result"]["combat"]
            turn_state = next(iter(combat.get("turnState", {}).values()), {})
            actor_id = turn_state.get("actorId", "unknown")
            parts.append(f"回合推进到 {actor_id}")
        elif tool_result["name"] == "apply_damage":
            result = tool_result["result"]
            character = result["character"]
            parts.append(f"{character['name']} 受到 {result['amount']} 点伤害")
        elif tool_result["name"] == "apply_healing":
            result = tool_result["result"]
            character = result["character"]
            parts.append(f"{character['name']} 恢复 {result['amount']} 点生命")
        elif tool_result["name"] == "apply_condition":
            result = tool_result["result"]
            character = result["character"]
            parts.append(f"{character['name']} 获得 {result['condition']} 状态")
        elif tool_result["name"] == "remove_condition":
            result = tool_result["result"]
            character = result["character"]
            parts.append(f"{character['name']} 移除 {result['condition']} 状态")
        elif tool_result["name"] == "spend_spell_slot":
            result = tool_result["result"]
            character = result["character"]
            parts.append(f"{character['name']} 消耗 {result['amount']} 个 {result['level']} 环法术位")
        elif tool_result["name"] == "restore_spell_slot":
            result = tool_result["result"]
            character = result["character"]
            parts.append(f"{character['name']} 恢复 {result['amount']} 个 {result['level']} 环法术位")
        elif tool_result["name"] == "spend_resource":
            result = tool_result["result"]
            character = result["character"]
            resource = result["resource"]
            parts.append(f"{character['name']} 消耗 {result['amount']} 点 {resource['name']}")
        elif tool_result["name"] == "restore_resource":
            result = tool_result["result"]
            character = result["character"]
            resource = result["resource"]
            parts.append(f"{character['name']} 恢复 {result['amount']} 点 {resource['name']}")
        elif tool_result["name"] == "restore_action_economy":
            result = tool_result["result"]
            parts.append(f"{result['actorId']} 恢复 {result['actionType']}")
        elif tool_result["name"] == "resolve_attack":
            result = tool_result["result"]
            parts.append(
                f"{result['attackerId']} 攻击 {result['targetId']}："
                f"{'命中' if result['hit'] else '未命中'}"
            )
    return "；".join(parts) + "。" if parts else "行动已记录。"


def _build_dm_messages(
    message: str,
    *,
    speaker: str,
    user_id: str,
    rule_context: str = "",
) -> list[tuple[str, str]]:
    messages = [
        ("system", DM_SYSTEM_PROMPT),
        ("system", _build_state_context(user_id=user_id)),
    ]
    if rule_context:
        messages.append(("system", rule_context))
    messages.append(("human", f"{speaker}: {message}"))
    return messages


def _build_rule_context(message: str, *, user_id: str) -> str:
    try:
        from playscript_agent.api.services.rag_service import build_rule_context

        return build_rule_context(message, user_id=user_id)
    except Exception:
        return ""


def _build_state_context(*, user_id: str) -> str:
    state = game_state.snapshot()
    player = game_state.find_player(user_id)
    controlled_character_id = player.get("characterId")
    controlled_character = (
        game_state.find_character(str(controlled_character_id))
        if controlled_character_id
        else None
    )
    current_state = {
        "current_user": player,
        "controlled_character": strip_image_payloads(controlled_character),
        "session": state["session"],
        "adventure": state.get("adventure", {}),
        "map": state["map"],
        "combat": state.get("combat", {}),
        "pending_actions": state.get("pendingActions", []),
        "tokens": state["tokens"],
        "characters": strip_image_payloads(state["characters"]),
        "recent_public_events": state["events"][-8:],
    }
    return (
        "Authoritative current_state JSON follows. Use it as the only source of truth "
        "for player character identity, race, class, HP, AC, skills, attacks, resources, spell slots, and conditions.\n"
        "Player users may only move, roll for, or spend resources on their controlled character. "
        "Do not call tools for monsters, map objects, or other player characters unless the current user is DM.\n"
        f"{json.dumps(current_state, ensure_ascii=False)}\n"
        f"{_build_adventure_context(state)}"
    )


def _build_adventure_context(state: dict[str, Any]) -> str:
    if state["session"].get("mode") == "character_creation":
        return ""
    try:
        from playscript_agent.api.services import adventure_service

        module_name = state.get("adventure", {}).get("moduleName") or "凡戴尔的失落矿坑"
        excerpt = adventure_service.opening_module_excerpt(str(module_name))
        scenes = adventure_service.scene_collection_summary(str(module_name))
    except Exception:
        return ""
    return (
        "Current adventure module excerpt follows. Use it to pace locations, clues, NPC motives, "
        "encounter triggers, and scene descriptions, but keep player-facing replies concise.\n"
        f"Available module scenes JSON: {json.dumps(scenes, ensure_ascii=False)}\n"
        f"{excerpt}"
    )


def strip_image_payloads(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_image_payloads(item) for item in value]
    if isinstance(value, dict):
        return {
            key: strip_image_payloads(item)
            for key, item in value.items()
            if key != "dataUrl"
        }
    return value


def _extract_tool_calls(response: Any, *, user_id: str) -> list[ToolCall]:
    raw_calls = getattr(response, "tool_calls", None) or []
    if not raw_calls:
        additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
        raw_calls = additional_kwargs.get("tool_calls", [])

    tool_calls: list[ToolCall] = []
    for raw_call in raw_calls:
        normalized = _normalize_tool_call(raw_call, user_id=user_id)
        if normalized is not None:
            tool_calls.append(normalized)
    return tool_calls


def _normalize_tool_call(raw_call: Any, *, user_id: str) -> ToolCall | None:
    if not isinstance(raw_call, dict):
        return None

    if "function" in raw_call:
        function = raw_call.get("function") or {}
        name = function.get("name")
        arguments = function.get("arguments", {})
    else:
        name = raw_call.get("name")
        arguments = raw_call.get("args", raw_call.get("arguments", {}))

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return None
    if not isinstance(arguments, dict):
        return None

    if name == "move_token":
        if not _can_use_tactical_grid():
            return None
        token_id = arguments.get("token_id", arguments.get("tokenId"))
        if token_id is None or "x" not in arguments or "y" not in arguments:
            return None
        return {
            "name": "move_token",
            "arguments": {
                "token_id": _canonical_token(str(token_id)),
                "x": int(arguments["x"]),
                "y": int(arguments["y"]),
            },
        }
    if name == "roll_dice":
        expression = arguments.get("expression")
        if expression is None:
            return None
        return {
            "name": "roll_dice",
            "arguments": {
                "expression": str(expression),
                "reason": str(arguments.get("reason", "chat roll")),
                "roller_id": _safe_roller_id(
                    arguments.get("roller_id", arguments.get("rollerId")),
                    user_id=user_id,
                ),
                "advantage": str(arguments.get("advantage", "normal")),
            },
        }
    if name in {
        "start_combat",
        "end_combat",
        "switch_exploration_scene",
        "end_turn",
        "advance_turn",
        "apply_damage",
        "apply_healing",
        "apply_condition",
        "remove_condition",
        "spend_spell_slot",
        "restore_spell_slot",
        "spend_resource",
        "restore_resource",
        "restore_action_economy",
        "resolve_attack",
        "resolve_saving_throw",
        "resolve_skill_check",
        "open_reaction_window",
        "resolve_reaction",
        "decline_reaction",
        "edit_map_layer",
        "set_map_background",
    }:
        return {"name": name, "arguments": _snake_case_arguments(arguments)}
    return None


def _filter_monster_turn_tool_calls(tool_calls: list[ToolCall], *, actor_id: str) -> list[ToolCall]:
    filtered: list[ToolCall] = []
    for tool_call in tool_calls:
        name = tool_call["name"]
        arguments = dict(tool_call["arguments"])
        if name not in MONSTER_TURN_TOOLS:
            continue
        if name == "move_token":
            token_id = arguments.get("token_id")
            if token_id is None or not _matches_actor(str(token_id), actor_id):
                continue
            arguments["token_id"] = actor_id
        elif name == "roll_dice":
            roller_id = arguments.get("roller_id")
            if roller_id is not None and not _matches_actor(str(roller_id), actor_id):
                arguments["roller_id"] = actor_id
            elif roller_id is None:
                arguments["roller_id"] = actor_id
        elif name == "end_turn":
            requested_actor = arguments.get("actor_id")
            if requested_actor is not None and not _matches_actor(str(requested_actor), actor_id):
                continue
            arguments["actor_id"] = actor_id
        elif name == "resolve_attack":
            if not _matches_actor(str(arguments.get("attacker_id", "")), actor_id):
                continue
            arguments["attacker_id"] = actor_id
        elif name in {"resolve_saving_throw", "resolve_skill_check"}:
            if not _matches_actor(str(arguments.get("actor_id", "")), actor_id):
                continue
            arguments["actor_id"] = actor_id
        elif name in {"spend_resource", "restore_resource"}:
            if not _matches_actor(str(arguments.get("character_id", "")), actor_id):
                continue
            arguments["character_id"] = actor_id
        elif name == "restore_action_economy":
            if not _matches_actor(str(arguments.get("actor_id", "")), actor_id):
                continue
            arguments["actor_id"] = actor_id
        filtered.append({"name": name, "arguments": arguments})
    if not any(tool_call["name"] == "end_turn" for tool_call in filtered):
        filtered.append({"name": "end_turn", "arguments": {"actor_id": actor_id}})
    return filtered


def _fallback_monster_turn_tool_calls(actor_id: str) -> list[ToolCall]:
    target_id = _nearest_living_player_actor_id(actor_id)
    if not target_id:
        return [{"name": "end_turn", "arguments": {"actor_id": actor_id}}]
    attack = _first_attack(actor_id)
    return [
        {
            "name": "resolve_attack",
            "arguments": {
                "attacker_id": actor_id,
                "target_id": target_id,
                "attack_bonus": attack["attack_bonus"],
                "damage_expression": attack["damage_expression"],
                "damage_type": attack["damage_type"],
                "advantage": "normal",
            },
        },
        {"name": "end_turn", "arguments": {"actor_id": actor_id}},
    ]


def _first_attack(actor_id: str) -> dict[str, Any]:
    try:
        character = game_state.find_character(actor_id)
    except ValueError:
        character = {}
    attacks = character.get("attacks") or []
    for attack in attacks:
        match = ATTACK_PATTERN.search(str(attack))
        if match:
            return {
                "attack_bonus": int(match.group("bonus")),
                "damage_expression": match.group("damage"),
                "damage_type": "untyped",
            }
    return {"attack_bonus": 0, "damage_expression": "1d4", "damage_type": "untyped"}


def _nearest_living_player_actor_id(actor_id: str) -> str | None:
    state = game_state.snapshot()
    try:
        actor_token = _token_for_actor(actor_id)
    except Exception:
        actor_token = None
    player_tokens = [
        token
        for token in state["tokens"]
        if token.get("kind") == "player" and _is_living_actor(str(token.get("actorId", token["id"])))
    ]
    if not player_tokens:
        return None
    if actor_token is None:
        return str(player_tokens[0].get("actorId", player_tokens[0]["id"]))
    target = min(
        player_tokens,
        key=lambda token: abs(int(token["x"]) - int(actor_token["x"])) + abs(int(token["y"]) - int(actor_token["y"])),
    )
    return str(target.get("actorId", target["id"]))


def _is_living_actor(actor_id: str) -> bool:
    try:
        character = game_state.find_character(actor_id)
    except ValueError:
        return False
    return int(character.get("hp", {}).get("current", 0)) > 0


def _is_current_actor_turn(actor_id: str) -> bool:
    state = game_state.snapshot()
    return bool(state["combat"].get("active")) and _matches_actor(game_state.current_combat_actor_id(), actor_id)


def _matches_actor(value: str, actor_id: str) -> bool:
    normalized = _normalize_actor_ref(value)
    actor_refs = {_normalize_actor_ref(actor_id)}
    try:
        token = _token_for_actor(actor_id)
        actor_refs.update(
            {
                _normalize_actor_ref(str(token["id"])),
                _normalize_actor_ref(str(token.get("actorId", token["id"]))),
                _normalize_actor_ref(str(token.get("name", ""))),
            }
        )
    except Exception:
        pass
    try:
        character = game_state.find_character(actor_id)
        actor_refs.update(
            {
                _normalize_actor_ref(str(character["id"])),
                _normalize_actor_ref(str(character.get("name", ""))),
            }
        )
    except ValueError:
        pass
    return normalized in actor_refs


def _normalize_actor_ref(value: str) -> str:
    return re.sub(r"\s+", "", _canonical_token(value).strip().lower())


def _can_use_tactical_grid() -> bool:
    state = game_state.snapshot()
    if "adventure" not in state:
        return True
    return state.get("session", {}).get("mode") == "combat"


def _extract_content(response: Any) -> str:
    content = getattr(response, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return str(content).strip() if content else ""


def _plan_move_call(message: str) -> ToolCall | None:
    for pattern in MOVE_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        token_id = _canonical_token(match.group("token"))
        x = int(match.group("x"))
        y = int(match.group("y"))
        return {
            "name": "move_token",
            "arguments": {
                "token_id": token_id,
                "x": x,
                "y": y,
            },
        }
    return None


def _plan_roll_call(message: str, *, speaker: str, user_id: str) -> ToolCall | None:
    expression = dice_service.find_inline_dice_expression(message)
    reason = "chat roll"
    lower_message = message.lower()

    if expression is None and any(
        keyword in lower_message
        for keyword in ["attack", "攻击", "射击", "hit"]
    ):
        expression = "1d20+5"
        reason = "attack roll"
    elif expression is None and any(
        keyword in lower_message
        for keyword in ["check", "调查", "侦查", "观察", "检定"]
    ):
        expression = "1d20+3"
        reason = "ability check"

    if expression is None:
        return None

    return {
        "name": "roll_dice",
        "arguments": {
            "expression": expression,
            "reason": reason,
            "roller_id": game_state.character_id_for_user(user_id) or speaker,
            "advantage": "normal",
        },
    }


def _canonical_token(value: str) -> str:
    normalized = value.strip().lower()
    return TOKEN_ALIASES.get(value.strip(), TOKEN_ALIASES.get(normalized, normalized))


def _token_for_actor(actor_id: str) -> dict[str, Any] | None:
    try:
        return game_state.actor_token(actor_id)
    except ValueError:
        return None


def _safe_roller_id(value: Any, *, user_id: str | None) -> str | None:
    requested = str(value).strip() if value is not None else ""
    fallback = game_state.character_id_for_user(user_id) if user_id else None
    if user_id is None:
        return requested or fallback
    if requested and game_state.can_roll_for_actor(user_id, requested):
        return requested
    if fallback and game_state.can_roll_for_actor(user_id, fallback):
        return fallback
    return user_id


def _snake_case_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "participantIds": "participant_ids",
        "actorId": "actor_id",
        "sourceId": "source_id",
        "targetId": "target_id",
        "characterId": "character_id",
        "attackerId": "attacker_id",
        "attackBonus": "attack_bonus",
        "damageExpression": "damage_expression",
        "damageType": "damage_type",
        "resourceName": "resource_name",
        "actionType": "action_type",
        "slotLevel": "level",
        "spellLevel": "level",
        "windowId": "window_id",
        "sceneId": "scene_id",
        "moduleName": "module_name",
    }
    return {aliases.get(key, key): value for key, value in arguments.items()}
