from __future__ import annotations

from typing import Any

from playscript_agent.api.services.game_state import game_state


def move_token(token_id: str, x: int, y: int) -> dict[str, Any]:
    token = game_state.move_token(token_id, x, y)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Map",
            "text": f"{token['name']} moved to ({x + 1}, {y + 1}).",
        }
    )
    return token
