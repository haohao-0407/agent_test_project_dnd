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
            "text": f"{token['name']} moved to ({x}, {y}).",
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


def edit_map_layer(layer: str, items: list[dict[str, Any]], *, user_id: str) -> dict[str, Any]:
    game_map = game_state.update_map_layer(layer, items, user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Map",
            "text": f"Map layer {layer} updated.",
        }
    )
    return game_map


def set_map_background(background: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    game_map = game_state.update_map_background(background, user_id=user_id)
    game_state.append_event(
        {
            "type": "system",
            "speaker": "Map",
            "text": f"Map background updated for {game_map['name']}.",
        }
    )
    return game_map
