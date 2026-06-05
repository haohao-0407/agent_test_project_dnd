from __future__ import annotations

from typing import Any

from playscript_agent.api.services.game_state import game_state


def move_token(token_id: str, x: int, y: int, *, user_id: str | None = None) -> dict[str, Any]:
    if user_id is not None:
        game_state.assert_can_control_token(user_id, token_id)
    token = game_state.move_token(token_id, x, y)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Map",
            "text": f"{token['name']} moved to ({x + 1}, {y + 1}).",
        }
    )
    return token


def update_map(updates: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    game_map = game_state.update_map(updates, user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Map",
            "text": f"Map {game_map['name']} updated.",
        }
    )
    return game_map
