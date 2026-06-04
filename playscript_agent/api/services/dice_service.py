from __future__ import annotations

import random
import re
from typing import Any

from playscript_agent.api.services.game_state import current_time, game_state


DICE_PATTERN = re.compile(r"^\s*(?:(\d*)d(\d+))\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)
INLINE_DICE_PATTERN = re.compile(r"(?<!\w)(\d*d\d+(?:\s*[+-]\s*\d+)?)(?!\w)", re.IGNORECASE)


def roll_dice(
    expression: str,
    *,
    reason: str,
    roller_id: str | None = None,
    advantage: str = "normal",
) -> dict[str, Any]:
    match = DICE_PATTERN.match(expression)
    if not match:
        raise ValueError("dice expression must look like 1d20+5")

    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int((match.group(3) or "0").replace(" ", ""))
    if count < 1 or count > 50:
        raise ValueError("dice count must be between 1 and 50")
    if sides < 2 or sides > 1000:
        raise ValueError("dice sides must be between 2 and 1000")
    if advantage not in {"normal", "advantage", "disadvantage"}:
        raise ValueError("advantage must be normal, advantage, or disadvantage")

    if advantage != "normal" and count == 1 and sides == 20:
        rolls = [random.randint(1, 20), random.randint(1, 20)]
        kept = [max(rolls) if advantage == "advantage" else min(rolls)]
    else:
        rolls = [random.randint(1, sides) for _ in range(count)]
        kept = rolls

    return {
        "expression": expression,
        "rolls": rolls,
        "kept": kept,
        "modifier": modifier,
        "total": sum(kept) + modifier,
        "reason": reason,
        "rollerId": roller_id,
        "advantage": advantage,
        "time": current_time(),
    }


def roll_and_record(
    expression: str,
    *,
    reason: str,
    roller_id: str | None = None,
    advantage: str = "normal",
) -> dict[str, Any]:
    result = roll_dice(
        expression,
        reason=reason,
        roller_id=roller_id,
        advantage=advantage,
    )
    game_state.append_event(
        {
            "type": "dice",
            "speaker": "Dice",
            "text": f"{result['expression']} = {result['total']} ({result['reason']})",
            "result": result,
        }
    )
    return result


def find_inline_dice_expression(text: str) -> str | None:
    match = INLINE_DICE_PATTERN.search(text)
    return match.group(1).replace(" ", "") if match else None
