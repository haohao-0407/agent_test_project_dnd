from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from playscript_agent.api.services import adventure_service, character_repository, chat_service, dice_service, map_service, monster_repository
from playscript_agent.api.services.game_state import game_state


TEST_CHARACTER_ROOT = Path(__file__).resolve().parents[1] / "document" / "characters" / ".test-permanent-repository"
TEST_MONSTER_ROOT = Path(__file__).resolve().parents[1] / "document" / "characters" / ".test-permanent-monsters"


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


def test_permanent_character_repository_stores_each_character_in_own_file(monkeypatch):
    character_root = TEST_CHARACTER_ROOT
    character_dir = character_root / "permanent"
    shutil.rmtree(character_root, ignore_errors=True)
    monkeypatch.setattr(character_repository, "PERMANENT_CHARACTER_DIR", character_dir)

    try:
        character_repository.create_permanent_character({
            "id": "hero-one",
            "name": "Hero One",
            "images": [
                {
                    "id": "portrait",
                    "purpose": "portrait",
                    "title": "Portrait",
                    "fileName": "portrait.png",
                    "mimeType": "image/png",
                    "size": 0,
                    "dataUrl": "data:image/png;base64,aGVsbG8=",
                    "notes": "",
                    "createdAt": "2026-06-05T00:00:00Z",
                }
            ],
        })
        character_repository.create_permanent_character({"id": "hero-two", "name": "Hero Two"})
        updated = character_repository.update_permanent_character(
            "hero-one",
            {"name": "Renamed Hero", "hp": {"current": 7, "max": 10, "temp": 0}},
        )

        assert updated["name"] == "Renamed Hero"
        assert updated["hp"]["current"] == 7
        assert (character_dir / "hero-one" / "character.json").exists()
        assert (character_dir / "hero-two" / "character.json").exists()
        assert (character_dir / "hero-one" / "images" / "portrait.png").exists()
        loaded_characters = character_repository.load_permanent_characters()
        hero_one = next(character for character in loaded_characters if character["id"] == "hero-one")
        assert {character["id"] for character in loaded_characters} == {
            "hero-one",
            "hero-two",
        }
        assert hero_one["images"][0]["path"] == "images/portrait.png"
        assert hero_one["images"][0]["url"] == "/character-assets/hero-one/images/portrait.png"
        assert "dataUrl" not in hero_one["images"][0]
    finally:
        shutil.rmtree(character_root, ignore_errors=True)


def test_permanent_character_repository_ignores_legacy_library_file(monkeypatch):
    character_root = TEST_CHARACTER_ROOT
    character_dir = character_root / "permanent"
    legacy_path = character_root / "old-library.json"
    shutil.rmtree(character_root, ignore_errors=True)
    character_root.mkdir(parents=True)
    legacy_path.write_text(
        json.dumps([
            {"id": "legacy-hero", "name": "Legacy Hero"},
            {"id": "legacy-mage", "name": "Legacy Mage"},
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(character_repository, "PERMANENT_CHARACTER_DIR", character_dir)

    try:
        characters = character_repository.load_permanent_characters()

        assert characters == []
        assert not character_dir.exists()
    finally:
        shutil.rmtree(character_root, ignore_errors=True)


def test_permanent_monster_repository_uses_bestiary_fields(monkeypatch):
    monster_root = TEST_MONSTER_ROOT
    shutil.rmtree(monster_root, ignore_errors=True)
    monkeypatch.setattr(monster_repository, "PERMANENT_MONSTER_DIR", monster_root)

    try:
        monster_repository.create_permanent_monster(
            {
                "id": "goblin",
                "name": "地精",
                "size": "小型",
                "type": "类人生物",
                "armorClass": "15 (皮甲, 盾牌)",
                "hitPoints": "7 (2d6)",
                "speed": "30 尺",
                "attributes": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
                "skills": "隐匿 +6",
                "challengeRating": "1/4 (XP 50; PB +2)",
                "actions": "弯刀 Scimitar. 近战攻击检定: +4，触及 5 尺。命中: 5 (1d6 + 2)挥砍伤害。",
            }
        )

        monsters = monster_repository.load_permanent_monsters()
        assert monsters[0]["challengeRating"].startswith("1/4")
        assert (monster_root / "goblin" / "monster.json").exists()
    finally:
        shutil.rmtree(monster_root, ignore_errors=True)


def test_bestiary_monster_converts_to_combat_character():
    character = monster_repository.bestiary_character_by_name("三角龙", character_id="tri-1")

    assert character is not None
    assert character["id"] == "tri-1"
    assert character["class"] == "Monster"
    assert character["ac"] == 14
    assert character["hp"]["max"] == 114
    assert character["attributes"]["STR"] == 22


def test_chat_state_context_strips_image_payloads():
    payload = {
        "images": [
            {
                "id": "portrait",
                "dataUrl": "data:image/png;base64,aGVsbG8=",
                "url": "/character-assets/hero/images/portrait.png",
            }
        ]
    }

    stripped = chat_service.strip_image_payloads(payload)

    assert "dataUrl" not in stripped["images"][0]
    assert stripped["images"][0]["url"] == "/character-assets/hero/images/portrait.png"


def test_dice_service_records_roll():
    result = dice_service.roll_and_record("1d20+5", reason="attack roll")

    assert 6 <= result["total"] <= 25
    assert result["expression"] == "1d20+5"
    assert game_state.snapshot()["events"][-1]["type"] == "dice"


def test_adventure_scene_browser_exposes_linked_lost_mine_scenes():
    browser = adventure_service.scene_browser()
    opening = next(scene for scene in browser["explorationScenes"] if scene["id"] == "triboar-trail-road")

    assert len(browser["explorationScenes"]) >= 80
    assert opening["backgroundUrl"].startswith("/module-assets/")
    assert opening["combatScene"]["id"] == "triboar-trail-ambush"
    assert opening["combatScene"]["monsterCount"] == 4


def test_dm_can_jump_exploration_scene_and_sync_adventure_state():
    state = adventure_service.switch_exploration_scene(
        user_id="dm",
        scene_id="sleeping-giant",
    )

    assert state["session"]["mode"] == "exploration"
    assert state["adventure"]["scene"] == "沉睡的巨人"
    assert state["adventure"]["explorationSceneId"] == "sleeping-giant"
    assert state["adventure"]["backgroundUrl"].endswith("/pictures/Player/exploration/sleeping-giant.png")
    assert state["adventure"]["combatSceneId"] == "phandalin-redbrand-street"
    assert state["events"][-1]["text"] == "Scene changed to 沉睡的巨人."


def test_only_dm_can_prepare_combat_scene():
    with pytest.raises(PermissionError):
        adventure_service.prepare_combat_scene(scene_id="triboar-trail-ambush", user_id="player-kael")


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

    assert kael["x"] == 5
    assert kael["y"] == 4
    assert [call["name"] for call in response["toolCalls"]] == [
        "move_token",
        "roll_dice",
    ]
    assert response["toolCalls"][0]["arguments"] == {
        "token_id": "kael",
        "x": 5,
        "y": 4,
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
    assert "移动到 (5, 4)" in state["events"][-1]["text"]
    assert "结果为" in state["events"][-1]["text"]


def test_chat_uses_llm_dm_for_plain_dialogue(monkeypatch):
    game_state.update_character(
        "kael",
        {
            "images": [
                {
                    "id": "portrait",
                    "purpose": "portrait",
                    "title": "Portrait",
                    "fileName": "portrait.png",
                    "mimeType": "image/png",
                    "size": 5,
                    "dataUrl": "data:image/png;base64,aGVsbG8=",
                    "notes": "",
                    "createdAt": "2026-06-05T00:00:00Z",
                }
            ]
        },
        user_id="player-kael",
    )
    fake_dm = FakeDmModel([FakeMessage(content="门后传来低沉的呼吸声，火光忽明忽暗。")])
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat("我听听门后有什么", speaker="player")
    state = response["state"]

    assert response["dmSource"] == "llm"
    assert response["toolCalls"] == []
    assert state["events"][-1]["type"] == "dm"
    assert state["events"][-1]["text"] == "门后传来低沉的呼吸声，火光忽明忽暗。"
    tool_names = [tool["name"] for tool in fake_dm.tools]
    assert tool_names[:2] == ["move_token", "roll_dice"]
    assert "update_character_state" not in tool_names
    assert "start_combat" in tool_names
    assert "resolve_attack" in tool_names
    assert "spend_spell_slot" in tool_names
    assert "spend_resource" in tool_names
    assert "edit_map_layer" in tool_names
    prompt_text = "\n".join(part for _, part in fake_dm.messages[0])
    assert '"class": "Wizard 3"' in prompt_text
    assert '"race": "High Elf"' in prompt_text
    assert "dataUrl" not in prompt_text
    assert "aGVsbG8=" not in prompt_text


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


def test_chat_uses_granular_llm_tools_for_damage_and_conditions(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "apply_damage",
                        "args": {"target_id": "kael", "amount": 12, "damage_type": "poison"},
                    },
                    {
                        "name": "apply_condition",
                        "args": {"target_id": "kael", "condition": "poisoned"},
                    },
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
            "name": "apply_damage",
            "arguments": {"target_id": "kael", "amount": 12, "damage_type": "poison"},
        },
        {
            "name": "apply_condition",
            "arguments": {"target_id": "kael", "condition": "poisoned"},
        },
    ]
    assert kael["hp"]["current"] == 12
    assert kael["conditions"] == ["poisoned"]


def test_chat_uses_granular_llm_tools_for_spell_slots_and_resources(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "spend_spell_slot",
                        "args": {"character_id": "mira", "level": 2, "amount": 1},
                    },
                    {
                        "name": "spend_resource",
                        "args": {"character_id": "kael", "resource_name": "Second Wind", "amount": 1},
                    },
                ]
            ),
            FakeMessage(content="资源消耗已记录。"),
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat("Mira 施放二环法术，Kael 使用 Second Wind", speaker="DM", user_id="dm")
    mira = next(character for character in response["state"]["characters"] if character["id"] == "mira")
    kael = next(character for character in response["state"]["characters"] if character["id"] == "kael")
    second_wind = next(resource for resource in kael["resources"] if resource["name"] == "Second Wind")

    assert [call["name"] for call in response["toolCalls"]] == ["spend_spell_slot", "spend_resource"]
    assert mira["spellcasting"]["slots"]["2"]["current"] == 0
    assert second_wind["current"] == 0


def test_legacy_update_character_state_tool_call_is_ignored(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                content="我需要使用更具体的规则工具。",
                tool_calls=[
                    {
                        "name": "update_character_state",
                        "args": {
                            "character_id": "kael",
                            "updates": {"hp": {"current": 1, "max": 30, "temp": 0}},
                        },
                    }
                ],
            ),
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat("把 Kael 的 HP 改成 1", speaker="Kael Player")
    kael = next(character for character in response["state"]["characters"] if character["id"] == "kael")

    assert response["toolCalls"] == []
    assert kael["hp"]["current"] == 24


def test_chat_llm_can_start_combat_with_dm_authority(monkeypatch):
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                tool_calls=[
                    {
                        "name": "start_combat",
                        "args": {"participant_ids": ["kael", "goblin-1"]},
                    }
                ]
            ),
            FakeMessage(content="战斗开始，先攻顺序已经建立。"),
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)

    response = chat_service.handle_chat(
        "战斗",
        speaker="Kael Player",
        user_id="player-kael",
    )

    assert response["toolCalls"] == [
        {
            "name": "start_combat",
            "arguments": {"participant_ids": ["kael", "goblin-1"]},
        }
    ]
    assert response["state"]["combat"]["active"] is True
    assert response["state"]["session"]["mode"] == "combat"
    assert response["state"]["events"][-1]["text"] == "战斗开始，先攻顺序已经建立。"


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


def test_player_roll_tool_call_coerces_unowned_roller_to_owned_character():
    result = chat_service.execute_tool_call(
        {
            "name": "roll_dice",
            "arguments": {
                "expression": "1d20+1",
                "reason": "ability check",
                "roller_id": "DM",
                "advantage": "normal",
            },
        },
        user_id="player-kael",
    )

    assert result["result"]["rollerId"] == "kael"


def test_map_repository_migrates_legacy_map_to_layered_map():
    from playscript_agent.api.services import map_repository

    game_map = map_repository.validate_map(
        {
            "id": "legacy",
            "name": "Legacy",
            "width": 4,
            "height": 4,
            "gridSize": 50,
            "terrain": [{"x": 1, "y": 1, "type": "wall"}],
            "annotations": [{"x": 2, "y": 2, "label": "door"}],
        }
    )

    assert game_map["layers"]["terrain"] == [{"x": 1, "y": 1, "type": "wall"}]
    assert game_map["layers"]["walls"] == [{"x": 1, "y": 1, "type": "wall"}]
    assert game_map["layers"]["annotations"] == [{"x": 2, "y": 2, "label": "door"}]
    assert game_map["background"]["url"] == ""
    assert game_map["terrain"] == game_map["layers"]["terrain"]


def test_combat_start_end_turn_and_damage(monkeypatch):
    from playscript_agent.api.services import combat_service

    monkeypatch.setattr("playscript_agent.api.services.game_state.random.randint", lambda low, high: 10)

    combat = combat_service.start_combat(["kael", "goblin-1"], user_id="dm")

    assert combat["active"] is True
    assert combat["round"] == 1
    assert {entry["actorId"] for entry in combat["initiativeOrder"]} == {"kael", "goblin-1"}

    current_actor = game_state.current_combat_actor_id()
    next_combat = combat_service.end_turn(current_actor, user_id="dm")

    assert next_combat["turnIndex"] == 1

    result = combat_service.apply_damage("goblin-1", 3, damage_type="slashing", user_id="dm")
    assert result["character"]["hp"]["current"] == 4


def test_combat_uses_agent_for_monster_turns_before_next_player(monkeypatch):
    monkeypatch.setattr("playscript_agent.api.services.game_state.random.randint", lambda low, high: 10)
    fake_dm = FakeDmModel(
        [
            FakeMessage(
                content="地精趁势挥刀，逼得 Kael 后退半步。",
                tool_calls=[
                    {
                        "name": "apply_damage",
                        "args": {"target_id": "kael", "amount": 3, "damage_type": "slashing"},
                    },
                    {
                        "name": "end_turn",
                        "args": {"actor_id": "goblin-1"},
                    },
                ],
            )
        ]
    )
    monkeypatch.setattr(chat_service, "get_llm", lambda role: fake_dm)
    monkeypatch.setattr(chat_service, "_build_rule_context", lambda message, *, user_id: "")
    game_state.start_combat(["goblin-1", "kael"], user_id="dm")

    assert game_state.current_combat_actor_id() == "goblin-1"

    combat = chat_service.advance_to_player_turn(user_id="player-kael")
    kael = game_state.find_character("kael")

    assert combat["turnState"]["kael"]["actorId"] == "kael"
    assert game_state.current_combat_actor_id() == "kael"
    assert kael["hp"]["current"] == 21
    assert game_state.snapshot()["events"][-1]["text"] == "地精趁势挥刀，逼得 Kael 后退半步。"
    prompt_text = "\n".join(part for _, part in fake_dm.messages[0])
    assert "Current monster actor_id: goblin-1" in prompt_text


def test_player_reaction_pending_requires_actor_control():
    game_state.start_combat(["kael", "goblin-1"], user_id="dm")
    window = game_state.open_reaction_window(
        trigger="leaves_reach",
        actor_id="kael",
        source_id="kael",
        user_id="player-kael",
    )

    assert window["status"] == "open"
    with pytest.raises(PermissionError):
        game_state.confirm_pending_action(window["id"], user_id="player-mira")
    confirmed = game_state.confirm_pending_action(window["id"], user_id="player-kael")
    assert confirmed["status"] == "confirmed"
