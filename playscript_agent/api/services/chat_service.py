from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from playscript_agent.api.services import dice_service, map_service
from playscript_agent.api.services.game_state import game_state
from playscript_agent.llm import get_llm


ToolName = Literal["move_token", "roll_dice"]


class ToolCall(TypedDict):
    name: ToolName
    arguments: dict[str, Any]


class DmPlan(TypedDict):
    tool_calls: list[ToolCall]
    content: str
    source: Literal["llm", "fallback"]


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
]

DM_SYSTEM_PROMPT = """You are the Dungeon Master for a DND tabletop web app.
Use tool calls for every action that changes game state, moves tokens, or rolls dice.
Do not reveal tool JSON, function names, or backend details in player-facing text.
If no tool is needed, answer in concise Chinese as the DM.
For map coordinates, players use 1-based visible coordinates, while tools require 0-based x/y.
Keep public replies short and based only on the known game state and tool results."""


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


def handle_chat(message: str, *, speaker: str = "player") -> dict[str, Any]:
    message = message.strip()
    if not message:
        raise ValueError("message is required")

    game_state.append_event({"type": "player", "speaker": speaker, "text": message})

    dm_plan = plan_dm_turn(message, speaker=speaker)
    tool_calls = dm_plan["tool_calls"]
    tool_results = [execute_tool_call(tool_call) for tool_call in tool_calls]
    dm_text = narrate_dm_response(
        message,
        speaker=speaker,
        tool_results=tool_results,
        planned_content=dm_plan["content"],
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


def plan_dm_turn(message: str, *, speaker: str) -> DmPlan:
    llm_plan = _plan_with_llm(message, speaker=speaker)
    if llm_plan is not None:
        return llm_plan
    return {
        "tool_calls": _fallback_plan_tool_calls(message, speaker=speaker),
        "content": "",
        "source": "fallback",
    }


def plan_tool_calls(message: str, *, speaker: str) -> list[ToolCall]:
    return plan_dm_turn(message, speaker=speaker)["tool_calls"]


def _fallback_plan_tool_calls(message: str, *, speaker: str) -> list[ToolCall]:
    tool_calls: list[ToolCall] = []
    move_call = _plan_move_call(message)
    if move_call:
        tool_calls.append(move_call)

    roll_call = _plan_roll_call(message, speaker=speaker)
    if roll_call:
        tool_calls.append(roll_call)

    return tool_calls


def _plan_with_llm(message: str, *, speaker: str) -> DmPlan | None:
    try:
        llm = get_llm("dm")
        tool_bound_llm = llm.bind_tools(DM_TOOL_SCHEMAS)
        response = tool_bound_llm.invoke(_build_dm_messages(message, speaker=speaker))
    except Exception:
        return None

    return {
        "tool_calls": _extract_tool_calls(response),
        "content": _extract_content(response),
        "source": "llm",
    }


def execute_tool_call(tool_call: ToolCall) -> dict[str, Any]:
    name = tool_call["name"]
    arguments = tool_call["arguments"]
    if name == "move_token":
        token = map_service.move_token(
            str(arguments["token_id"]),
            int(arguments["x"]),
            int(arguments["y"]),
        )
        return {"name": name, "result": {"token": token}}
    if name == "roll_dice":
        result = dice_service.roll_and_record(
            str(arguments["expression"]),
            reason=str(arguments.get("reason", "chat roll")),
            roller_id=arguments.get("roller_id"),
            advantage=str(arguments.get("advantage", "normal")),
        )
        return {"name": name, "result": result}
    raise ValueError(f"unsupported tool call: {name}")


def narrate_dm_response(
    message: str,
    *,
    speaker: str,
    tool_results: list[dict[str, Any]],
    planned_content: str,
) -> str:
    fallback = build_result_message(tool_results) if tool_results else planned_content.strip()
    if not fallback:
        fallback = build_result_message([])
    if not tool_results:
        return fallback

    try:
        llm = get_llm("dm")
        response = llm.invoke(
            [
                ("system", DM_SYSTEM_PROMPT),
                (
                    "system",
                    "Write one concise Chinese DM reply using only the tool results. "
                    "Do not mention JSON, function calls, tools, or hidden backend details.",
                ),
                ("human", f"Speaker: {speaker}\nPlayer action: {message}\nTool results: {json.dumps(tool_results, ensure_ascii=False)}"),
            ]
        )
    except Exception:
        return fallback

    content = _extract_content(response)
    return content or fallback


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


def _build_dm_messages(message: str, *, speaker: str) -> list[tuple[str, str]]:
    return [
        ("system", DM_SYSTEM_PROMPT),
        ("system", _build_state_context()),
        ("human", f"{speaker}: {message}"),
    ]


def _build_state_context() -> str:
    state = game_state.snapshot()
    game_map = state["map"]
    tokens = ", ".join(
        f"{token['id']}({token['name']}) at visible ({token['x'] + 1}, {token['y'] + 1})"
        for token in state["tokens"]
    )
    characters = ", ".join(
        f"{character['id']}({character['name']} HP {character['hp']['current']}/{character['hp']['max']} AC {character['ac']})"
        for character in state["characters"]
    )
    recent_events = "\n".join(
        f"- {event['speaker']}: {event['text']}" for event in state["events"][-8:]
    )
    return (
        f"Map: {game_map['name']} visible size {game_map['width']}x{game_map['height']}.\n"
        f"Tokens: {tokens}.\n"
        f"Characters: {characters}.\n"
        f"Recent public events:\n{recent_events}"
    )


def _extract_tool_calls(response: Any) -> list[ToolCall]:
    raw_calls = getattr(response, "tool_calls", None) or []
    if not raw_calls:
        additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
        raw_calls = additional_kwargs.get("tool_calls", [])

    tool_calls: list[ToolCall] = []
    for raw_call in raw_calls:
        normalized = _normalize_tool_call(raw_call)
        if normalized is not None:
            tool_calls.append(normalized)
    return tool_calls


def _normalize_tool_call(raw_call: Any) -> ToolCall | None:
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
                "token_id": str(token_id),
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
                "roller_id": arguments.get("roller_id", arguments.get("rollerId")),
                "advantage": str(arguments.get("advantage", "normal")),
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


def _plan_roll_call(message: str, *, speaker: str) -> ToolCall | None:
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
            "roller_id": speaker,
            "advantage": "normal",
        },
    }


def _canonical_token(value: str) -> str:
    normalized = value.strip().lower()
    return TOKEN_ALIASES.get(value.strip(), TOKEN_ALIASES.get(normalized, normalized))
