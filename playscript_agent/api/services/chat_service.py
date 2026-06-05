from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from playscript_agent.api.services import dice_service, map_service
from playscript_agent.api.services.game_state import game_state
from playscript_agent.llm import get_llm


ToolName = Literal["move_token", "roll_dice", "update_character_state"]


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
                    "description": "Internal 0-based grid x coordinate. If the player says column 5, pass x=4.",
                },
                "y": {
                    "type": "integer",
                    "description": "Internal 0-based grid y coordinate. If the player says row 4, pass y=3.",
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
    {
        "name": "update_character_state",
        "description": (
            "Update a DND 5e character card when game state changes. Use this for HP, temp HP, "
            "death saves, conditions, resources, hit dice, spell slots, prepared spells, equipment, "
            "or other character card fields."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "string",
                    "description": "Character id or name, such as kael or mira.",
                },
                "updates": {
                    "type": "object",
                    "description": (
                        "Partial character card update using current_state field names. "
                        "Examples: {'hp': {'current': 12, 'max': 18, 'temp': 0}}, "
                        "{'conditions': ['poisoned']}, or "
                        "{'spellcasting': {'slots': {'1': {'max': 4, 'current': 2}}}}."
                    ),
                },
            },
            "required": ["character_id", "updates"],
        },
    },
]

DM_SYSTEM_PROMPT = """You are the Dungeon Master for a DND tabletop web app.
Use tool calls for every action that changes game state, moves tokens, rolls dice, or changes a character card.
Do not reveal tool JSON, function names, or backend details in player-facing text.
If no tool is needed, answer in concise Chinese as the DM.
For map coordinates, players use 1-based visible coordinates, while tools require 0-based x/y.
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
    return {
        "toolCalls": tool_calls,
        "toolResults": tool_results,
        "dmSource": dm_plan["source"],
        "state": game_state.snapshot(),
    }


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
    if name == "move_token":
        token = map_service.move_token(
            str(arguments["token_id"]),
            int(arguments["x"]),
            int(arguments["y"]),
            user_id=user_id,
        )
        return {"name": name, "result": {"token": token}}
    if name == "roll_dice":
        roller_id = arguments.get("roller_id")
        if user_id is not None and not game_state.can_roll_for_actor(
            user_id,
            str(roller_id) if roller_id is not None else None,
        ):
            raise PermissionError(f"user {user_id} cannot roll for {roller_id}")
        result = dice_service.roll_and_record(
            str(arguments["expression"]),
            reason=str(arguments.get("reason", "chat roll")),
            roller_id=roller_id,
            advantage=str(arguments.get("advantage", "normal")),
        )
        return {"name": name, "result": result}
    if name == "update_character_state":
        character = game_state.update_character(
            str(arguments["character_id"]),
            dict(arguments["updates"]),
            user_id=user_id or "dm",
        )
        return {"name": name, "result": {"character": character}}
    raise ValueError(f"unsupported tool call: {name}")


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
            parts.append(f"{token['name']} 移动到 ({token['x'] + 1}, {token['y'] + 1})")
        elif tool_result["name"] == "roll_dice":
            result = tool_result["result"]
            parts.append(f"{result['expression']} 结果为 {result['total']}")
    return "；".join(parts) + "。"


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
        "controlled_character": controlled_character,
        "session": state["session"],
        "map": state["map"],
        "tokens": state["tokens"],
        "characters": state["characters"],
        "recent_public_events": state["events"][-8:],
    }
    return (
        "Authoritative current_state JSON follows. Use it as the only source of truth "
        "for player character identity, race, class, HP, AC, skills, attacks, resources, spell slots, and conditions.\n"
        "Player users may only move, roll for, or update their controlled character. "
        "Do not call tools for monsters, map objects, or other player characters unless the current user is DM.\n"
        f"{json.dumps(current_state, ensure_ascii=False)}"
    )


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
                "roller_id": arguments.get("roller_id", arguments.get("rollerId"))
                or game_state.character_id_for_user(user_id)
                or user_id,
                "advantage": str(arguments.get("advantage", "normal")),
            },
        }
    if name == "update_character_state":
        character_id = arguments.get("character_id", arguments.get("characterId"))
        updates = arguments.get("updates")
        if character_id is None or not isinstance(updates, dict):
            return None
        return {
            "name": "update_character_state",
            "arguments": {
                "character_id": _canonical_token(str(character_id)),
                "updates": updates,
            },
        }
    return None


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
        # User-facing coordinates are 1-based; map state is 0-based.
        x = int(match.group("x")) - 1
        y = int(match.group("y")) - 1
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
