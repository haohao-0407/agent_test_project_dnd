from __future__ import annotations

import re
from typing import Any

from playscript_agent.api.services import dice_service, map_service
from playscript_agent.api.services.game_state import game_state


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
    tool_results: list[dict[str, Any]] = []

    move_result = _try_move_from_message(message)
    if move_result is not None:
        tool_results.append(move_result)

    dice_result = _try_roll_from_message(message, speaker=speaker)
    if dice_result is not None:
        tool_results.append(dice_result)

    if tool_results:
        summary = "; ".join(result["summary"] for result in tool_results)
        dm_text = f"Tool calls resolved: {summary}."
    else:
        dm_text = (
            "Action recorded. Try commands like 'move kael to 5,4', "
            "'roll 1d20+3', or 'attack with 1d20+5'."
        )

    game_state.append_event({"type": "dm", "speaker": "DM", "text": dm_text})
    return {"toolResults": tool_results, "state": game_state.snapshot()}


def _try_move_from_message(message: str) -> dict[str, Any] | None:
    for pattern in MOVE_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        token_id = _canonical_token(match.group("token"))
        # Chat commands are player-facing and use 1-based grid coordinates.
        x = int(match.group("x")) - 1
        y = int(match.group("y")) - 1
        token = map_service.move_token(token_id, x, y)
        return {
            "type": "move_token",
            "token": token,
            "summary": f"{token['name']} -> ({x + 1}, {y + 1})",
        }
    return None


def _try_roll_from_message(message: str, *, speaker: str) -> dict[str, Any] | None:
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

    result = dice_service.roll_and_record(
        expression,
        reason=reason,
        roller_id=speaker,
    )
    return {
        "type": "roll_dice",
        "result": result,
        "summary": f"{result['expression']} = {result['total']}",
    }


def _canonical_token(value: str) -> str:
    normalized = value.strip().lower()
    return TOKEN_ALIASES.get(value.strip(), TOKEN_ALIASES.get(normalized, normalized))
