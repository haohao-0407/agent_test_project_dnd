from __future__ import annotations

import pytest

from playscript_agent.api.services import chat_service, dice_service, map_service
from playscript_agent.api.services.game_state import game_state


class FakeMessage:
    def __init__(self, *, content: str = "", tool_calls: list[dict] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.additional_kwargs = {}


class FakeDmModel:
    def __init__(self, responses: list[FakeMessage]):
        self.responses = responses
        self.messages: list[list[tuple[str, str]]] = []
        self.tools: list[dict] = []

    def bind_tools(self, tools: list[dict]) -> "FakeDmModel":
        self.tools = tools
        return self

    def invoke(self, messages: list[tuple[str, str]]) -> FakeMessage:
        self.messages.append(messages)
        return self.responses.pop(0)


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


def test_dm_can_update_map_but_players_cannot():
    updated = game_state.update_map(
        {"terrain": [{"x": 0, "y": 0, "type": "water"}]},
        user_id="dm",
        persist=False,
    )

    assert updated["terrain"] == [{"x": 0, "y": 0, "type": "water"}]
    with pytest.raises(PermissionError):
        game_state.update_map({"terrain": []}, user_id="player-kael", persist=False)


def test_map_update_rejects_wall_under_token():
    with pytest.raises(ValueError):
        game_state.update_map(
            {"terrain": [{"x": 2, "y": 3, "type": "wall"}]},
            user_id="dm",
            persist=False,
        )


def test_player_can_only_move_owned_token():
    token = map_service.move_token("kael", 4, 3, user_id="player-kael")

    assert token["id"] == "kael"
    with pytest.raises(PermissionError):
        map_service.move_token("mira", 4, 3, user_id="player-kael")
    with pytest.raises(PermissionError):
        map_service.move_token("goblin-1", 4, 3, user_id="player-kael")


def test_player_can_only_update_owned_character_card():
    character = game_state.update_character(
        "kael",
        {"hp": {"current": 20, "max": 30, "temp": 0}},
        user_id="player-kael",
    )

    assert character["hp"]["current"] == 20
    with pytest.raises(PermissionError):
        game_state.update_character(
            "mira",
            {"hp": {"current": 10, "max": 18, "temp": 0}},
            user_id="player-kael",
        )


def test_dice_service_records_roll():
    result = dice_service.roll_and_record("1d20+5", reason="attack roll")

    assert 6 <= result["total"] <= 25
    assert result["expression"] == "1d20+5"
    assert game_state.snapshot()["events"][-1]["type"] == "dice"


def test_chat_can_move_token_and_roll_dice(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "get_llm",
        lambda role: (_ for _ in ()).throw(RuntimeError("LLM disabled for fallback test")),
    )

    response = chat_service.handle_chat(
        "move kael to 5,4 and roll 1d20+2",
        speaker="player",
    )
    state = response["state"]
    kael = next(token for token in state["tokens"] if token["id"] == "kael")

    assert kael["x"] == 4
    assert kael["y"] == 3
    assert [call["name"] for call in response["toolCalls"]] == [
        "move_token",
        "roll_dice",
    ]
    assert response["toolCalls"][0]["arguments"] == {
        "token_id": "kael",
        "x": 4,
        "y": 3,
    }
    assert response["toolCalls"][1]["arguments"]["expression"] == "1d20+2"
    assert [result["name"] for result in response["toolResults"]] == [
        "move_token",
        "roll_dice",
    ]
    assert state["events"][-1]["type"] == "dm"
    assert "Tool calls resolved" not in state["events"][-1]["text"]
    assert "move_token" not in state["events"][-1]["text"]
    assert "roll_dice" not in state["events"][-1]["text"]
    assert "移动到" in state["events"][-1]["text"]
    assert "结果为" in state["events"][-1]["text"]


def test_chat_uses_llm_dm_for_plain_dialogue(monkeypatch):
    fake_dm = FakeDmModel([FakeMessage(content="门后传来低沉的呼吸声，火光忽明忽暗。")])
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat("我听听门后有什么", speaker="player")
    state = response["state"]

    assert response["dmSource"] == "llm"
    assert response["toolCalls"] == []
    assert state["events"][-1]["type"] == "dm"
    assert state["events"][-1]["text"] == "门后传来低沉的呼吸声，火光忽明忽暗。"
    assert [tool["name"] for tool in fake_dm.tools] == [
        "move_token",
        "roll_dice",
        "update_character_state",
    ]
    prompt_text = "\n".join(part for _, part in fake_dm.messages[0])
    assert '"class": "Wizard 3"' in prompt_text
    assert '"race": "High Elf"' in prompt_text


def test_chat_uses_llm_tool_calls_and_dm_narration(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "move_token",
                        "args": {"token_id": "kael", "x": 4, "y": 3},
                    },
                    {
                        "name": "roll_dice",
                        "args": {
                            "expression": "1d20+2",
                            "reason": "perception check",
                            "roller_id": "kael",
                            "advantage": "normal",
                        },
                    },
                ]
            ),
            FakeMessage(content="Kael 稳稳移动到门边，检定结果已经公开。"),
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat("Kael 靠近门口并观察", speaker="player")
    state = response["state"]
    kael = next(token for token in state["tokens"] if token["id"] == "kael")

    assert response["dmSource"] == "llm"
    assert [call["name"] for call in response["toolCalls"]] == [
        "move_token",
        "roll_dice",
    ]
    assert kael["x"] == 4
    assert kael["y"] == 3
    assert state["events"][-1]["text"] == "Kael 稳稳移动到门边，检定结果已经公开。"
    assert "move_token" not in state["events"][-1]["text"]
    assert "roll_dice" not in state["events"][-1]["text"]
    assert len(fake_dm.messages) == 2


def test_chat_uses_llm_tool_call_to_update_character_state(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "update_character_state",
                        "args": {
                            "character_id": "kael",
                            "updates": {
                                "hp": {"current": 12, "max": 30, "temp": 0},
                                "conditions": ["poisoned"],
                            },
                        },
                    }
                ]
            ),
            FakeMessage(content="Kael 的伤势已记录。"),
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat("Kael 受到 12 点伤害并中毒", speaker="Kael Player")
    kael = next(character for character in response["state"]["characters"] if character["id"] == "kael")

    assert response["toolCalls"] == [
        {
            "name": "update_character_state",
            "arguments": {
                "character_id": "kael",
                "updates": {
                    "hp": {"current": 12, "max": 30, "temp": 0},
                    "conditions": ["poisoned"],
                },
            },
        }
    ]
    assert kael["hp"]["current"] == 12
    assert kael["conditions"] == ["poisoned"]


def test_chat_rejects_llm_tool_call_for_unowned_token(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "move_token",
                        "args": {"token_id": "mira", "x": 4, "y": 3},
                    }
                ]
            )
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    with pytest.raises(PermissionError):
        chat_service.handle_chat(
            "我让 Mira 往前走",
            speaker="Kael Player",
            user_id="player-kael",
        )


def test_chat_includes_rule_context_in_planning_prompt(monkeypatch):
    fake_dm = FakeDmModel([FakeMessage(content="The door waits.")])
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)
    monkeypatch.setattr(
        chat_service,
        "_build_rule_context",
        lambda message, *, user_id: "RAG_CONTEXT: Armor Class protects creatures.",
    )

    response = chat_service.handle_chat("How does Armor Class work?", speaker="player")

    assert response["dmSource"] == "llm"
    prompt_text = "\n".join(part for _, part in fake_dm.messages[0])
    assert "RAG_CONTEXT: Armor Class protects creatures." in prompt_text
    assert '"class": "Wizard 3"' in prompt_text


def test_chat_reuses_rule_context_in_tool_narration_prompt(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "roll_dice",
                        "args": {
                            "expression": "1d20+3",
                            "reason": "perception check",
                            "roller_id": "kael",
                            "advantage": "normal",
                        },
                    }
                ]
            ),
            FakeMessage(content="Kael makes the check."),
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)
    monkeypatch.setattr(
        chat_service,
        "_build_rule_context",
        lambda message, *, user_id: "RAG_CONTEXT: Use perception rules.",
    )

    response = chat_service.handle_chat("I check the door.", speaker="player")

    assert response["dmSource"] == "llm"
    assert len(fake_dm.messages) == 2
    narration_prompt = "\n".join(part for _, part in fake_dm.messages[1])
    assert "RAG_CONTEXT: Use perception rules." in narration_prompt
    assert '"class": "Wizard 3"' in narration_prompt
