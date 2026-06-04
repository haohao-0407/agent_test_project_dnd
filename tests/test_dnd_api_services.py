from __future__ import annotations

import pytest

from playscript_agent.api.services import chat_service, dice_service, map_service
from playscript_agent.api.services.game_state import game_state


def setup_function() -> None:
    game_state.reset()


def test_map_service_moves_token_and_records_event():
    token = map_service.move_token("kael", 4, 3)
    state = game_state.snapshot()

    assert token["id"] == "kael"
    assert token["x"] == 4
    assert token["y"] == 3
    assert state["tokens"][0]["x"] == 4
    assert state["events"][-1]["type"] == "system"


def test_map_service_rejects_blocked_square():
    with pytest.raises(ValueError):
        map_service.move_token("kael", 4, 1)


def test_dice_service_records_roll():
    result = dice_service.roll_and_record("1d20+5", reason="attack roll")

    assert 6 <= result["total"] <= 25
    assert result["expression"] == "1d20+5"
    assert game_state.snapshot()["events"][-1]["type"] == "dice"


def test_chat_can_move_token_and_roll_dice():
    response = chat_service.handle_chat(
        "move kael to 5,4 and roll 1d20+2",
        speaker="player",
    )
    state = response["state"]
    kael = next(token for token in state["tokens"] if token["id"] == "kael")

    assert kael["x"] == 4
    assert kael["y"] == 3
    assert [result["type"] for result in response["toolResults"]] == [
        "move_token",
        "roll_dice",
    ]
    assert state["events"][-1]["type"] == "dm"
