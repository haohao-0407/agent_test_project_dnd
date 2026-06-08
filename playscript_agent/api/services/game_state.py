from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random
import secrets
from threading import RLock
from typing import Any

from playscript_agent.api.services import map_repository


ABILITY_KEYS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
CHARACTER_EDITABLE_FIELDS = {
    "id",
    "ownerUserId",
    "name",
    "playerName",
    "class",
    "classes",
    "level",
    "race",
    "subrace",
    "background",
    "alignment",
    "experience",
    "inspiration",
    "proficiencyBonus",
    "hp",
    "hitDice",
    "deathSaves",
    "ac",
    "initiative",
    "speed",
    "attributes",
    "abilities",
    "savingThrows",
    "skills",
    "skillDetails",
    "attacks",
    "attackDetails",
    "actions",
    "actionDetails",
    "conditions",
    "defenses",
    "senses",
    "proficiencies",
    "languages",
    "equipment",
    "currency",
    "features",
    "featureDetails",
    "traits",
    "traitDetails",
    "spellcasting",
    "resources",
    "personality",
    "appearance",
    "images",
    "notes",
}
CORE_CONDITIONS = {
    "prone",
    "grappled",
    "restrained",
    "poisoned",
    "stunned",
    "unconscious",
    "incapacitated",
    "concentrating",
    "dead",
    "dying",
}
DEFAULT_SESSION_ID = "default"
SESSION_TOKEN_TTL = timedelta(hours=12)


@dataclass(frozen=True, slots=True)
class Principal:
    session_id: str
    user_id: str
    role: str


@dataclass(frozen=True, slots=True)
class SessionToken:
    token: str
    principal: Principal
    expires_at: datetime


def default_combat_state() -> dict[str, Any]:
    return {
        "active": False,
        "round": 0,
        "turnIndex": 0,
        "initiativeOrder": [],
        "turnState": {},
        "reactionWindows": [],
        "participants": [],
    }


def default_turn_state(actor_id: str) -> dict[str, Any]:
    return {
        "actorId": actor_id,
        "actionAvailable": True,
        "bonusActionAvailable": True,
        "reactionAvailable": True,
        "objectInteractionAvailable": True,
        "movementUsed": 0,
        "movementMax": 30,
    }


def blank_spell_slots() -> dict[str, dict[str, int]]:
    return {str(level): {"max": 0, "current": 0} for level in range(1, 10)}


def ability_details(attributes: dict[str, int]) -> dict[str, dict[str, int | bool]]:
    return {
        key: {
            "score": int(attributes.get(key, 10)),
            "modifier": (int(attributes.get(key, 10)) - 10) // 2,
            "saveProficient": False,
        }
        for key in ABILITY_KEYS
    }


def base_character_card(character_id: str, name: str) -> dict[str, Any]:
    attributes = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
    return {
        "id": character_id,
        "ownerUserId": None,
        "name": name,
        "playerName": "",
        "class": "Fighter 1",
        "classes": [{"name": "Fighter", "subclass": "", "level": 1, "hitDie": "d10"}],
        "level": 1,
        "race": "Human",
        "subrace": "",
        "background": "Adventurer",
        "alignment": "Neutral",
        "experience": 0,
        "inspiration": False,
        "proficiencyBonus": 2,
        "hp": {"current": 10, "max": 10, "temp": 0},
        "hitDice": [{"die": "d10", "max": 1, "current": 1}],
        "deathSaves": {"successes": 0, "failures": 0},
        "ac": 10,
        "initiative": 0,
        "speed": 30,
        "attributes": attributes,
        "abilities": ability_details(attributes),
        "savingThrows": [],
        "skills": [],
        "skillDetails": [],
        "attacks": [],
        "attackDetails": [],
        "actions": [],
        "actionDetails": [],
        "conditions": [],
        "defenses": {"resistances": [], "immunities": [], "vulnerabilities": []},
        "senses": {"passivePerception": 10, "passiveInvestigation": 10, "passiveInsight": 10, "other": []},
        "proficiencies": {"armor": [], "weapons": [], "tools": []},
        "languages": [],
        "equipment": {"items": [], "attunedItems": [], "carryingCapacity": 0},
        "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
        "features": [],
        "featureDetails": [],
        "traits": [],
        "traitDetails": [],
        "spellcasting": {
            "ability": "",
            "saveDc": 0,
            "attackBonus": 0,
            "slots": blank_spell_slots(),
            "pactSlots": {"slotLevel": 0, "max": 0, "current": 0},
            "spellsKnown": [],
            "spellsPrepared": [],
        },
        "resources": [],
        "personality": {"traits": "", "ideals": "", "bonds": "", "flaws": ""},
        "appearance": {"age": "", "height": "", "weight": "", "eyes": "", "skin": "", "hair": ""},
        "images": [],
        "notes": "",
    }


def normalize_character_card(raw_character: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_character, dict):
        raise ValueError("character must be an object")
    character_id = str(raw_character.get("id") or raw_character.get("name") or "character").strip()
    name = str(raw_character.get("name") or character_id).strip()
    if not character_id or not name:
        raise ValueError("character id and name are required")

    normalized = base_character_card(character_id, name)
    for key, value in raw_character.items():
        if key in CHARACTER_EDITABLE_FIELDS:
            if isinstance(normalized.get(key), dict) and isinstance(value, dict):
                normalized[key].update(deepcopy(value))
            else:
                normalized[key] = deepcopy(value)

    normalized["id"] = str(normalized["id"]).strip()
    normalized["name"] = str(normalized["name"]).strip()
    normalized["attributes"] = {
        key: int(normalized.get("attributes", {}).get(key, 10))
        for key in ABILITY_KEYS
    }
    existing_abilities = normalized.get("abilities") if isinstance(normalized.get("abilities"), dict) else {}
    normalized["abilities"] = ability_details(normalized["attributes"])
    for key, detail in existing_abilities.items():
        if key in normalized["abilities"] and isinstance(detail, dict):
            normalized["abilities"][key].update(deepcopy(detail))
            normalized["abilities"][key]["score"] = normalized["attributes"][key]
            normalized["abilities"][key]["modifier"] = (normalized["attributes"][key] - 10) // 2

    normalized["hp"] = {
        "current": int(normalized.get("hp", {}).get("current", 0)),
        "max": max(1, int(normalized.get("hp", {}).get("max", 1))),
        "temp": max(0, int(normalized.get("hp", {}).get("temp", 0))),
    }
    normalized["ac"] = int(normalized.get("ac", 10))
    normalized["speed"] = int(normalized.get("speed", 30))
    normalized["level"] = int(normalized.get("level", 1))
    normalized["proficiencyBonus"] = int(normalized.get("proficiencyBonus", 2))
    normalized["images"] = normalize_character_images(normalized.get("images"))

    spellcasting = normalized.get("spellcasting") if isinstance(normalized.get("spellcasting"), dict) else {}
    normalized["spellcasting"] = base_character_card(character_id, name)["spellcasting"]
    normalized["spellcasting"].update(deepcopy(spellcasting))

    slots = blank_spell_slots()
    raw_slots = normalized["spellcasting"].get("slots", {})
    if isinstance(raw_slots, dict):
        for level, slot in raw_slots.items():
            if str(level) in slots and isinstance(slot, dict):
                slots[str(level)] = {
                    "max": max(0, int(slot.get("max", 0))),
                    "current": max(0, int(slot.get("current", 0))),
                }
    normalized["spellcasting"]["slots"] = slots
    return normalized


def normalize_character_images(raw_images: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_images, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, raw_image in enumerate(raw_images):
        if not isinstance(raw_image, dict):
            continue
        data_url = str(raw_image.get("dataUrl") or "").strip()
        image_path = str(raw_image.get("path") or "").strip()
        image_url = str(raw_image.get("url") or "").strip()
        if not data_url and not image_path and not image_url:
            continue
        image_id = str(raw_image.get("id") or f"image-{index + 1}").strip()
        image = {
            "id": image_id or f"image-{index + 1}",
            "purpose": str(raw_image.get("purpose") or "other").strip() or "other",
            "title": str(raw_image.get("title") or "").strip(),
            "fileName": str(raw_image.get("fileName") or "").strip(),
            "mimeType": str(raw_image.get("mimeType") or "").strip(),
            "size": max(0, int(raw_image.get("size") or 0)),
            "path": image_path,
            "url": image_url,
            "notes": str(raw_image.get("notes") or ""),
            "createdAt": str(raw_image.get("createdAt") or ""),
        }
        if data_url:
            image["dataUrl"] = data_url
        normalized.append(image)
    return normalized


_DEFAULT_STATE: dict[str, Any] = {
    "session": {
        "id": "demo-dnd-session",
        "title": "Ash Frontier",
        "mode": "exploration",
        "round": 1,
        "currentTurn": "kael",
    },
    "players": [
        {
            "id": "player-kael",
            "displayName": "Kael Player",
            "characterId": "kael",
            "role": "player",
            "joined": False,
            "ready": False,
        },
        {
            "id": "player-mira",
            "displayName": "Mira Player",
            "characterId": "mira",
            "role": "player",
            "joined": False,
            "ready": False,
        },
        {
            "id": "dm",
            "displayName": "DM",
            "characterId": None,
            "role": "dm",
            "joined": False,
            "ready": False,
        },
    ],
    "map": map_repository.load_default_map(),
    "tokens": [
        {"id": "kael", "actorId": "kael", "name": "Kael", "kind": "player", "x": 2, "y": 3},
        {"id": "mira", "actorId": "mira", "name": "Mira", "kind": "player", "x": 3, "y": 4},
        {"id": "goblin-1", "actorId": "goblin-1", "name": "Goblin", "kind": "monster", "x": 8, "y": 3},
        {"id": "wolf-1", "actorId": "wolf-1", "name": "Wolf", "kind": "monster", "x": 9, "y": 5},
    ],
    "characters": [
        {
            "id": "kael",
            "ownerUserId": "player-kael",
            "name": "Kael",
            "playerName": "Kael Player",
            "class": "Fighter 3",
            "classes": [{"name": "Fighter", "subclass": "Champion", "level": 3, "hitDie": "d10"}],
            "level": 3,
            "race": "Human",
            "background": "Soldier",
            "alignment": "Neutral Good",
            "experience": 900,
            "proficiencyBonus": 2,
            "hp": {"current": 24, "max": 30, "temp": 0},
            "hitDice": [{"die": "d10", "max": 3, "current": 3}],
            "deathSaves": {"successes": 0, "failures": 0},
            "ac": 17,
            "initiative": 1,
            "speed": 30,
            "attributes": {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 11, "CHA": 9},
            "skills": ["Athletics", "Intimidation", "Perception"],
            "attacks": ["Longsword +5 1d8+3", "Shortbow +3 1d6+1"],
            "conditions": [],
            "proficiencies": {
                "armor": ["Light", "Medium", "Heavy", "Shields"],
                "weapons": ["Simple", "Martial"],
                "tools": ["Dice set"],
            },
            "languages": ["Common"],
            "equipment": {"items": ["Longsword", "Shortbow", "Chain mail", "Shield"], "attunedItems": [], "carryingCapacity": 240},
            "features": ["Second Wind", "Action Surge", "Improved Critical"],
            "resources": [{"name": "Second Wind", "max": 1, "current": 1, "reset": "short rest"}],
        },
        {
            "id": "mira",
            "ownerUserId": "player-mira",
            "name": "Mira",
            "playerName": "Mira Player",
            "class": "Wizard 3",
            "classes": [{"name": "Wizard", "subclass": "Evocation", "level": 3, "hitDie": "d6"}],
            "level": 3,
            "race": "High Elf",
            "background": "Sage",
            "alignment": "Chaotic Good",
            "experience": 900,
            "proficiencyBonus": 2,
            "hp": {"current": 15, "max": 18, "temp": 0},
            "hitDice": [{"die": "d6", "max": 3, "current": 3}],
            "deathSaves": {"successes": 0, "failures": 0},
            "ac": 13,
            "initiative": 2,
            "speed": 30,
            "attributes": {"STR": 8, "DEX": 14, "CON": 12, "INT": 17, "WIS": 13, "CHA": 11},
            "skills": ["Arcana", "Investigation", "History"],
            "attacks": ["Fire Bolt +5 1d10", "Dagger +4 1d4+2"],
            "conditions": ["concentrating"],
            "proficiencies": {"armor": [], "weapons": ["Dagger", "Quarterstaff", "Light crossbow"], "tools": []},
            "languages": ["Common", "Elvish", "Draconic"],
            "equipment": {"items": ["Spellbook", "Arcane focus", "Dagger"], "attunedItems": [], "carryingCapacity": 120},
            "features": ["Arcane Recovery", "Sculpt Spells", "Fey Ancestry"],
            "spellcasting": {
                "ability": "INT",
                "saveDc": 13,
                "attackBonus": 5,
                "slots": {
                    "1": {"max": 4, "current": 3},
                    "2": {"max": 2, "current": 1},
                },
                "spellsKnown": ["Fire Bolt", "Mage Hand", "Magic Missile", "Shield", "Misty Step"],
                "spellsPrepared": ["Magic Missile", "Shield", "Detect Magic", "Misty Step"],
            },
            "resources": [{"name": "Arcane Recovery", "max": 1, "current": 1, "reset": "long rest"}],
        },
        {
            "id": "goblin-1",
            "ownerUserId": None,
            "name": "Goblin",
            "class": "Monster",
            "race": "Goblin",
            "hp": {"current": 7, "max": 7, "temp": 0},
            "ac": 15,
            "initiative": 2,
            "speed": 30,
            "attributes": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
            "skills": ["Stealth"],
            "attacks": ["Scimitar +4 1d6+2", "Shortbow +4 1d6+2"],
            "conditions": [],
        },
        {
            "id": "wolf-1",
            "ownerUserId": None,
            "name": "Wolf",
            "class": "Monster",
            "race": "Wolf",
            "hp": {"current": 11, "max": 11, "temp": 0},
            "ac": 13,
            "initiative": 2,
            "speed": 40,
            "attributes": {"STR": 12, "DEX": 15, "CON": 12, "INT": 3, "WIS": 12, "CHA": 6},
            "skills": ["Perception", "Stealth"],
            "attacks": ["Bite +4 2d4+2"],
            "conditions": [],
        },
    ],
    "combat": default_combat_state(),
    "pendingActions": [],
    "events": [
        {
            "type": "dm",
            "speaker": "DM",
            "text": "Rain fades around the roadside ruin. A scorched door hangs open, and something breathes in the dark.",
            "time": "12:00",
        }
    ],
}


class GameStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state = fresh_adventure_start_state()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def reset(self) -> None:
        with self._lock:
            self._state = fresh_default_state()

    def reset_to_adventure_start(self) -> None:
        with self._lock:
            self._state = fresh_adventure_start_state()

    def update_player_display_name(self, user_id: str, display_name: str) -> dict[str, Any]:
        with self._lock:
            player = self.find_player(user_id)
            player["displayName"] = display_name
            return deepcopy(player)

    def update_player_presence(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        joined: bool | None = None,
        ready: bool | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            player = self.find_player(user_id)
            if display_name is not None:
                player["displayName"] = display_name
            if joined is not None:
                player["joined"] = joined
            if ready is not None:
                player["ready"] = ready
            return deepcopy(player)

    def set_player_ready(self, user_id: str, ready: bool) -> dict[str, Any]:
        with self._lock:
            player = self.find_player(user_id)
            if player.get("role") == "dm":
                raise PermissionError("DM does not need to ready up")
            if ready and not player.get("characterId"):
                raise PermissionError("create a character before readying up")
            player["ready"] = ready
            return self.snapshot()

    def append_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            event.setdefault("time", current_time())
            self._state["events"].append(event)
            self._state["events"] = self._state["events"][-80:]

    def move_token(self, token_id: str, x: int, y: int) -> dict[str, Any]:
        with self._lock:
            if not self.is_in_bounds(x, y):
                raise ValueError("target square is outside the map")
            if self.is_blocked(x, y):
                raise ValueError("target square is blocked")
            token = self.find_token(token_id)
            self._spend_combat_movement(token, x, y)
            token["x"] = x
            token["y"] = y
            return deepcopy(token)

    def update_character(
        self,
        character_id: str,
        updates: dict[str, Any],
        *,
        user_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            self.assert_can_control_character(user_id, character_id)
            character = self.find_character(character_id)
            for key, value in updates.items():
                if key not in CHARACTER_EDITABLE_FIELDS or key == "id":
                    raise ValueError(f"character field cannot be updated: {key}")
                character[key] = deepcopy(value)
            character.update(normalize_character_card(character))
            return deepcopy(character)

    def create_character(
        self,
        character: dict[str, Any],
        *,
        user_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            next_character = normalize_character_card(character)
            if not next_character.get("ownerUserId"):
                next_character["ownerUserId"] = None if self.is_dm(user_id) else user_id
            existing_ids = {item["id"].lower() for item in self._state["characters"]}
            if next_character["id"].lower() in existing_ids:
                raise ValueError(f"character already exists: {next_character['id']}")
            self._state["characters"].append(next_character)
            if not self.is_dm(user_id):
                player = self.find_player(user_id)
                if not player.get("characterId"):
                    player["characterId"] = next_character["id"]
                player["ready"] = False
            return deepcopy(next_character)

    def start_adventure(
        self,
        *,
        user_id: str,
        module_name: str,
        game_map: dict[str, Any],
        monsters: list[dict[str, Any]],
        opening_text: str,
        source: str,
        exploration_scene_id: str = "",
        exploration_scene_name: str = "",
        background_url: str = "",
        combat_scene_id: str = "",
        combat_scene_name: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                character_id = self.character_id_for_user(user_id)
                if not character_id:
                    raise PermissionError("create a character before starting the adventure")

            player_characters = self._player_characters()
            if not player_characters:
                raise ValueError("at least one player character is required")

            next_map = map_repository.validate_map(game_map)
            monster_characters = [
                normalize_character_card(monster.get("character", {}))
                for monster in monsters
            ]
            player_positions = self._starting_positions(next_map, len(player_characters))
            player_tokens = [
                {
                    "id": character["id"],
                    "actorId": character["id"],
                    "name": character["name"],
                    "kind": "player",
                    "x": position[0],
                    "y": position[1],
                }
                for character, position in zip(player_characters, player_positions, strict=False)
            ]
            monster_tokens = [
                {
                    "id": str(monster.get("id") or monster.get("character", {}).get("id")),
                    "actorId": str(monster.get("id") or monster.get("character", {}).get("id")),
                    "name": str(monster.get("name") or monster.get("character", {}).get("name") or "Monster"),
                    "kind": "monster",
                    "x": int(monster.get("x", 0)),
                    "y": int(monster.get("y", 0)),
                }
                for monster in monsters
            ]

            self._state["session"] = {
                "id": "demo-dnd-session",
                "title": module_name,
                "mode": "exploration",
                "round": 1,
                "currentTurn": player_tokens[0]["id"] if player_tokens else "",
            }
            self._state["adventure"] = {
                "moduleName": module_name,
                "chapter": "地精箭矢",
                "scene": exploration_scene_name or next_map["name"],
                "explorationSceneId": exploration_scene_id,
                "backgroundUrl": background_url,
                "combatSceneId": combat_scene_id,
                "combatSceneName": combat_scene_name or next_map["name"],
                "source": source,
                "startedAt": current_time(),
            }
            self._state["map"] = next_map
            self._state["tokens"] = player_tokens + monster_tokens
            player_character_ids = {character["id"] for character in player_characters}
            self._state["characters"] = [
                normalize_character_card(character)
                for character in self._state["characters"]
                if character["id"] in player_character_ids
            ] + monster_characters
            self._state["combat"] = default_combat_state()
            self._state["pendingActions"] = []
            self._state["events"] = [
                {
                    "type": "system",
                    "speaker": "Adventure",
                    "text": f"{module_name} 已开始，地图由 {source} 生成。",
                    "time": current_time(),
                },
                {
                    "type": "dm",
                    "speaker": "DM",
                    "text": opening_text,
                    "time": current_time(),
                },
            ]
            self._assert_tokens_fit_map(next_map)
            return self.snapshot()

    def set_combat_scene(
        self,
        *,
        game_map: dict[str, Any],
        monsters: list[dict[str, Any]],
        combat_scene_id: str,
        combat_scene_name: str,
        user_id: str = "dm",
        module_name: str | None = None,
        chapter: str | None = None,
        exploration_scene_id: str | None = None,
        exploration_scene_name: str | None = None,
        background_url: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot change scenes")
            player_characters = self._player_characters()
            if not player_characters:
                raise ValueError("at least one player character is required")

            next_map = map_repository.validate_map(game_map)
            monster_characters = [
                normalize_character_card(monster.get("character", {}))
                for monster in monsters
            ]
            player_positions = self._starting_positions(next_map, len(player_characters))
            player_tokens = [
                {
                    "id": character["id"],
                    "actorId": character["id"],
                    "name": character["name"],
                    "kind": "player",
                    "x": position[0],
                    "y": position[1],
                }
                for character, position in zip(player_characters, player_positions, strict=False)
            ]
            monster_tokens = [
                {
                    "id": str(monster.get("id") or monster.get("character", {}).get("id")),
                    "actorId": str(monster.get("id") or monster.get("character", {}).get("id")),
                    "name": str(monster.get("name") or monster.get("character", {}).get("name") or "Monster"),
                    "kind": "monster",
                    "x": int(monster.get("x", 0)),
                    "y": int(monster.get("y", 0)),
                }
                for monster in monsters
            ]
            player_character_ids = {character["id"] for character in player_characters}
            self._state["map"] = next_map
            self._state["tokens"] = player_tokens + monster_tokens
            self._state["characters"] = [
                normalize_character_card(character)
                for character in self._state["characters"]
                if character["id"] in player_character_ids
            ] + monster_characters
            self._state.setdefault("adventure", {})
            if module_name is not None:
                self._state["adventure"]["moduleName"] = module_name
                self._state["session"]["title"] = module_name
            if chapter is not None:
                self._state["adventure"]["chapter"] = chapter
            if exploration_scene_id is not None:
                self._state["adventure"]["explorationSceneId"] = exploration_scene_id
            if exploration_scene_name:
                self._state["adventure"]["scene"] = exploration_scene_name
            elif combat_scene_name:
                self._state["adventure"]["scene"] = combat_scene_name
            if background_url is not None:
                self._state["adventure"]["backgroundUrl"] = background_url
            self._state["adventure"]["combatSceneId"] = combat_scene_id
            self._state["adventure"]["combatSceneName"] = combat_scene_name
            self._assert_tokens_fit_map(next_map)
            return self.snapshot()

    def set_exploration_scene(
        self,
        *,
        user_id: str,
        module_name: str,
        chapter: str,
        exploration_scene_id: str,
        exploration_scene_name: str,
        background_url: str,
        combat_scene_id: str = "",
        combat_scene_name: str = "",
        source: str = "module",
    ) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot change scenes")
            self._state["session"]["title"] = module_name
            self._state["session"]["mode"] = "exploration"
            self._state["session"]["currentTurn"] = ""
            self._state["adventure"] = {
                **self._state.get("adventure", {}),
                "moduleName": module_name,
                "chapter": chapter,
                "scene": exploration_scene_name,
                "explorationSceneId": exploration_scene_id,
                "backgroundUrl": background_url,
                "combatSceneId": combat_scene_id,
                "combatSceneName": combat_scene_name,
                "source": source,
                "startedAt": self._state.get("adventure", {}).get("startedAt") or current_time(),
            }
            self._state["combat"] = default_combat_state()
            self._state["pendingActions"] = []
            return self.snapshot()

    def update_map(
        self,
        updates: dict[str, Any],
        *,
        user_id: str,
        persist: bool = True,
    ) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot edit the map")
            game_map = map_repository.apply_map_updates(self._state["map"], updates)
            self._assert_tokens_fit_map(game_map)
            self._state["map"] = game_map
            if persist:
                map_repository.save_default_map(game_map)
            return deepcopy(game_map)

    def update_map_layer(self, layer: str, items: list[dict[str, Any]], *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot edit the map")
            if layer not in self._state["map"]["layers"]:
                raise ValueError(f"unknown map layer: {layer}")
            updates = {"layers": {**self._state["map"]["layers"], layer: deepcopy(items)}}
            game_map = map_repository.apply_map_updates(self._state["map"], updates)
            self._assert_tokens_fit_map(game_map)
            self._state["map"] = game_map
            map_repository.save_default_map(game_map)
            return deepcopy(game_map)

    def update_map_background(self, background: dict[str, Any], *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot edit the map")
            game_map = map_repository.apply_map_updates(self._state["map"], {"background": background})
            self._state["map"] = game_map
            map_repository.save_default_map(game_map)
            return deepcopy(game_map)

    def calibrate_grid(self, grid: dict[str, Any], *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot edit the map")
            game_map = map_repository.apply_map_updates(self._state["map"], {"grid": grid})
            self._state["map"] = game_map
            map_repository.save_default_map(game_map)
            return deepcopy(game_map)

    def start_combat(self, participant_ids: list[str] | None = None, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot start combat")
            participants = participant_ids or [token["actorId"] for token in self._state["tokens"]]
            order = []
            for actor_id in participants:
                character = self.find_character(actor_id)
                dex_mod = self.ability_modifier(character, "DEX")
                roll = random.randint(1, 20)
                order.append(
                    {
                        "actorId": character["id"],
                        "name": character["name"],
                        "initiative": roll + dex_mod,
                        "roll": roll,
                        "dexModifier": dex_mod,
                    }
                )
            order.sort(key=lambda item: (item["initiative"], item["dexModifier"], item["name"]), reverse=True)
            current_actor = order[0]["actorId"] if order else ""
            self._state["combat"] = {
                "active": True,
                "round": 1 if order else 0,
                "turnIndex": 0,
                "initiativeOrder": order,
                "turnState": {current_actor: self._turn_state_for_actor(current_actor)} if current_actor else {},
                "reactionWindows": [],
                "participants": participants,
            }
            self._state["session"]["mode"] = "combat"
            self._state["session"]["round"] = self._state["combat"]["round"]
            self._state["session"]["currentTurn"] = current_actor
            return deepcopy(self._state["combat"])

    def end_combat(self, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot end combat")
            self._state["combat"] = default_combat_state()
            self._state["session"]["mode"] = "exploration"
            return deepcopy(self._state["combat"])

    def end_turn(self, actor_id: str | None = None, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            combat = self._state["combat"]
            if not combat["active"]:
                raise ValueError("combat is not active")
            current_actor = self.current_combat_actor_id()
            actor_id = actor_id or current_actor
            if actor_id != current_actor:
                raise ValueError(f"it is not {actor_id}'s turn")
            if not self.is_dm(user_id):
                self.assert_can_control_actor(user_id, actor_id)
            return self._advance_turn_locked()

    def advance_turn(self, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                raise PermissionError(f"user {user_id} cannot force turn advancement")
            if not self._state["combat"]["active"]:
                raise ValueError("combat is not active")
            return self._advance_turn_locked()

    def spend_action(self, actor_id: str, action_type: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self.is_dm(user_id):
                self.assert_can_control_actor(user_id, actor_id)
            turn_state = self._require_turn_state(actor_id)
            key = {
                "action": "actionAvailable",
                "bonus_action": "bonusActionAvailable",
                "reaction": "reactionAvailable",
                "object_interaction": "objectInteractionAvailable",
            }.get(action_type)
            if key is None:
                raise ValueError(f"unknown action type: {action_type}")
            if not turn_state[key]:
                raise ValueError(f"{actor_id} has already spent {action_type}")
            turn_state[key] = False
            return deepcopy(turn_state)

    def apply_damage(self, target_id: str, amount: int, *, damage_type: str = "untyped", user_id: str) -> dict[str, Any]:
        with self._lock:
            self._assert_can_change_combatant(user_id, target_id)
            character = self.find_character(target_id)
            amount = max(0, int(amount))
            hp = deepcopy(character["hp"])
            absorbed = min(hp.get("temp", 0), amount)
            hp["temp"] = max(0, hp.get("temp", 0) - absorbed)
            hp["current"] = max(0, hp["current"] - (amount - absorbed))
            character["hp"] = hp
            self._sync_life_conditions(character)
            return {"character": deepcopy(character), "amount": amount, "damageType": damage_type, "absorbed": absorbed}

    def apply_healing(self, target_id: str, amount: int, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self._assert_can_change_combatant(user_id, target_id)
            character = self.find_character(target_id)
            amount = max(0, int(amount))
            hp = deepcopy(character["hp"])
            hp["current"] = min(hp["max"], hp["current"] + amount)
            character["hp"] = hp
            self._sync_life_conditions(character)
            return {"character": deepcopy(character), "amount": amount}

    def apply_condition(self, target_id: str, condition: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self._assert_can_change_combatant(user_id, target_id)
            normalized = str(condition).strip().lower()
            if normalized not in CORE_CONDITIONS:
                raise ValueError(f"unsupported condition: {condition}")
            character = self.find_character(target_id)
            if normalized not in character["conditions"]:
                character["conditions"].append(normalized)
            return {"character": deepcopy(character), "condition": normalized}

    def remove_condition(self, target_id: str, condition: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self._assert_can_change_combatant(user_id, target_id)
            normalized = str(condition).strip().lower()
            character = self.find_character(target_id)
            character["conditions"] = [item for item in character["conditions"] if item != normalized]
            return {"character": deepcopy(character), "condition": normalized}

    def spend_spell_slot(self, character_id: str, level: int | str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self.assert_can_control_character(user_id, character_id)
            character = self.find_character(character_id)
            slot_level = self._normalize_spell_slot_level(level)
            amount = self._normalize_resource_amount(amount)
            slot = character["spellcasting"]["slots"][slot_level]
            if int(slot.get("current", 0)) < amount:
                raise ValueError(f"{character['name']} does not have enough level {slot_level} spell slots")
            slot["current"] = int(slot.get("current", 0)) - amount
            return {
                "character": deepcopy(character),
                "level": slot_level,
                "amount": amount,
                "slot": deepcopy(slot),
            }

    def restore_spell_slot(self, character_id: str, level: int | str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self.assert_can_control_character(user_id, character_id)
            character = self.find_character(character_id)
            slot_level = self._normalize_spell_slot_level(level)
            amount = self._normalize_resource_amount(amount)
            slot = character["spellcasting"]["slots"][slot_level]
            before = int(slot.get("current", 0))
            slot["current"] = min(int(slot.get("max", 0)), before + amount)
            restored = slot["current"] - before
            return {
                "character": deepcopy(character),
                "level": slot_level,
                "amount": restored,
                "slot": deepcopy(slot),
            }

    def spend_resource(self, character_id: str, resource_name: str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self.assert_can_control_character(user_id, character_id)
            character = self.find_character(character_id)
            amount = self._normalize_resource_amount(amount)
            resource = self._find_character_resource(character, resource_name)
            if int(resource.get("current", 0)) < amount:
                raise ValueError(f"{character['name']} does not have enough {resource['name']}")
            resource["current"] = int(resource.get("current", 0)) - amount
            return {
                "character": deepcopy(character),
                "resource": deepcopy(resource),
                "amount": amount,
            }

    def restore_resource(self, character_id: str, resource_name: str, amount: int = 1, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            self.assert_can_control_character(user_id, character_id)
            character = self.find_character(character_id)
            amount = self._normalize_resource_amount(amount)
            resource = self._find_character_resource(character, resource_name)
            before = int(resource.get("current", 0))
            resource["current"] = min(int(resource.get("max", 0)), before + amount)
            restored = resource["current"] - before
            return {
                "character": deepcopy(character),
                "resource": deepcopy(resource),
                "amount": restored,
            }

    def open_reaction_window(
        self,
        *,
        trigger: str,
        actor_id: str,
        source_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            if not self._state["combat"]["active"]:
                raise ValueError("combat is not active")
            if not self.is_dm(user_id):
                self.assert_can_control_actor(user_id, source_id)
            actor_state = self._turn_state_for_actor(actor_id)
            available = []
            if actor_state["reactionAvailable"] and trigger == "leaves_reach":
                available.append({"id": "opportunity_attack", "label": "Opportunity Attack"})
            window = {
                "id": f"reaction-{len(self._state['combat']['reactionWindows']) + 1}",
                "trigger": trigger,
                "actorId": actor_id,
                "sourceId": source_id,
                "availableReactions": available,
                "status": "open" if available else "closed",
                "createdAt": current_time(),
            }
            self._state["combat"]["reactionWindows"].append(window)
            if available and not self.is_dm(user_id):
                self._state["pendingActions"].append(
                    {
                        "id": window["id"],
                        "type": "reaction",
                        "actorId": actor_id,
                        "requestedBy": user_id,
                        "status": "pending",
                        "payload": deepcopy(window),
                    }
                )
            return deepcopy(window)

    def resolve_reaction(self, window_id: str, reaction_id: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            window = self._find_reaction_window(window_id)
            self.assert_can_control_actor(user_id, window["actorId"])
            if window["status"] != "open":
                raise ValueError("reaction window is not open")
            if reaction_id not in {item["id"] for item in window["availableReactions"]}:
                raise ValueError(f"reaction is not available: {reaction_id}")
            turn_state = self._turn_state_for_actor(window["actorId"])
            if not turn_state["reactionAvailable"]:
                raise ValueError(f"{window['actorId']} has already spent reaction")
            turn_state["reactionAvailable"] = False
            window["status"] = "resolved"
            window["resolvedReactionId"] = reaction_id
            self._complete_pending(window_id, "confirmed")
            return deepcopy(window)

    def decline_reaction(self, window_id: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            window = self._find_reaction_window(window_id)
            self.assert_can_control_actor(user_id, window["actorId"])
            window["status"] = "declined"
            self._complete_pending(window_id, "declined")
            return deepcopy(window)

    def confirm_pending_action(self, action_id: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            action = self._find_pending_action(action_id)
            self.assert_can_control_actor(user_id, action["actorId"])
            action["status"] = "confirmed"
            return deepcopy(action)

    def decline_pending_action(self, action_id: str, *, user_id: str) -> dict[str, Any]:
        with self._lock:
            action = self._find_pending_action(action_id)
            self.assert_can_control_actor(user_id, action["actorId"])
            action["status"] = "declined"
            return deepcopy(action)

    def find_token(self, token_id_or_name: str) -> dict[str, Any]:
        normalized = normalize_token_name(token_id_or_name)
        for token in self._state["tokens"]:
            if token["id"].lower() == normalized or token["name"].lower() == normalized:
                return token
        raise ValueError(f"unknown token: {token_id_or_name}")

    def actor_token(self, actor_id: str) -> dict[str, Any]:
        normalized = normalize_token_name(actor_id)
        for token in self._state["tokens"]:
            if normalize_token_name(token.get("actorId", token["id"])) == normalized or token["id"].lower() == normalized:
                return token
        raise ValueError(f"unknown token for actor: {actor_id}")

    def find_character(self, character_id: str) -> dict[str, Any]:
        normalized = normalize_token_name(character_id)
        for character in self._state["characters"]:
            if character["id"].lower() == normalized or character["name"].lower() == normalized:
                return character
        raise ValueError(f"unknown character: {character_id}")

    def find_player(self, user_id: str) -> dict[str, Any]:
        normalized = normalize_token_name(user_id)
        for player in self._state["players"]:
            if player["id"].lower() == normalized:
                return player
        raise PermissionError(f"unknown user: {user_id}")

    def character_id_for_user(self, user_id: str) -> str | None:
        player = self.find_player(user_id)
        character_id = player.get("characterId")
        return str(character_id) if character_id else None

    def is_dm(self, user_id: str) -> bool:
        return self.find_player(user_id).get("role") == "dm"

    def assert_can_control_token(self, user_id: str, token_id: str) -> None:
        if self.is_dm(user_id):
            return
        token = self.find_token(token_id)
        character_id = self.character_id_for_user(user_id)
        if token["kind"] != "player" or token["id"] != character_id:
            raise PermissionError(f"user {user_id} cannot control token {token_id}")

    def assert_can_control_actor(self, user_id: str, actor_id: str) -> None:
        if self.is_dm(user_id):
            return
        character_id = self.character_id_for_user(user_id)
        if normalize_token_name(actor_id) != normalize_token_name(str(character_id)):
            raise PermissionError(f"user {user_id} cannot control actor {actor_id}")

    def assert_can_control_character(self, user_id: str, character_id: str) -> None:
        if self.is_dm(user_id):
            return
        character = self.find_character(character_id)
        if character.get("ownerUserId") == user_id:
            return
        owned_character_id = self.character_id_for_user(user_id)
        if normalize_token_name(character_id) != normalize_token_name(str(owned_character_id)):
            raise PermissionError(f"user {user_id} cannot modify character {character_id}")

    def can_roll_for_actor(self, user_id: str, actor_id: str | None) -> bool:
        if actor_id is None or self.is_dm(user_id):
            return True
        normalized_actor = normalize_token_name(actor_id)
        if normalized_actor == normalize_token_name(user_id):
            return True
        character_id = self.character_id_for_user(user_id)
        if not character_id:
            return False
        character = self.find_character(character_id)
        return normalized_actor in {
            normalize_token_name(character_id),
            normalize_token_name(character["name"]),
        }

    def is_in_bounds(self, x: int, y: int) -> bool:
        game_map = self._state["map"]
        return 0 <= x < game_map["width"] and 0 <= y < game_map["height"]

    def terrain_at(self, x: int, y: int) -> str | None:
        for terrain in self._state["map"]["terrain"]:
            if terrain["x"] == x and terrain["y"] == y:
                return terrain["type"]
        return None

    def is_blocked(self, x: int, y: int) -> bool:
        if self.terrain_at(x, y) == "wall":
            return True
        layers = self._state["map"].get("layers", {})
        blocked_layers = [*layers.get("walls", []), *layers.get("obstacles", [])]
        return any(item["x"] == x and item["y"] == y for item in blocked_layers)

    def ability_modifier(self, character: dict[str, Any], ability: str) -> int:
        key = ability.upper()
        ability_detail = character.get("abilities", {}).get(key)
        if isinstance(ability_detail, dict) and "modifier" in ability_detail:
            return int(ability_detail["modifier"])
        return (int(character.get("attributes", {}).get(key, 10)) - 10) // 2

    def current_combat_actor_id(self) -> str:
        combat = self._state["combat"]
        order = combat.get("initiativeOrder", [])
        if not order:
            return ""
        return str(order[combat["turnIndex"]]["actorId"])

    def _assert_tokens_fit_map(self, game_map: dict[str, Any]) -> None:
        wall_squares = {
            (terrain["x"], terrain["y"])
            for terrain in game_map["terrain"]
            if terrain["type"] == "wall"
        }
        wall_squares.update(
            (wall["x"], wall["y"])
            for wall in game_map.get("layers", {}).get("walls", [])
        )
        for token in self._state["tokens"]:
            x = token["x"]
            y = token["y"]
            if not (0 <= x < game_map["width"] and 0 <= y < game_map["height"]):
                raise ValueError(f"map update would leave token {token['id']} outside the map")
            if (x, y) in wall_squares:
                raise ValueError(f"map update would place a wall under token {token['id']}")

    def _player_characters(self) -> list[dict[str, Any]]:
        character_by_id = {character["id"]: character for character in self._state["characters"]}
        characters: list[dict[str, Any]] = []
        for player in self._state["players"]:
            if player.get("role") != "player" or not player.get("characterId"):
                continue
            character = character_by_id.get(str(player["characterId"]))
            if character is not None:
                characters.append(character)
        return characters

    def _starting_positions(self, game_map: dict[str, Any], count: int) -> list[tuple[int, int]]:
        preferred = [(2, game_map["height"] - 3), (2, game_map["height"] - 2), (1, game_map["height"] - 3), (3, game_map["height"] - 3), (3, game_map["height"] - 2)]
        positions: list[tuple[int, int]] = []
        blocked = {
            (item["x"], item["y"])
            for item in [
                *game_map.get("terrain", []),
                *game_map.get("layers", {}).get("walls", []),
                *game_map.get("layers", {}).get("obstacles", []),
            ]
            if item.get("type") in {"wall", "obstacle"}
        }
        for x, y in preferred:
            candidate = (min(max(x, 0), game_map["width"] - 1), min(max(y, 0), game_map["height"] - 1))
            if candidate not in blocked and candidate not in positions:
                positions.append(candidate)
            if len(positions) >= count:
                return positions
        for y in range(game_map["height"]):
            for x in range(game_map["width"]):
                candidate = (x, y)
                if candidate not in blocked and candidate not in positions:
                    positions.append(candidate)
                if len(positions) >= count:
                    return positions
        return positions

    def _advance_turn_locked(self) -> dict[str, Any]:
        combat = self._state["combat"]
        order = combat["initiativeOrder"]
        combat["turnIndex"] = (combat["turnIndex"] + 1) % len(order)
        if combat["turnIndex"] == 0:
            combat["round"] += 1
        current_actor = self.current_combat_actor_id()
        combat["turnState"] = {current_actor: self._turn_state_for_actor(current_actor)}
        combat["reactionWindows"] = [
            window for window in combat["reactionWindows"] if window.get("status") == "open"
        ]
        self._state["session"]["round"] = combat["round"]
        self._state["session"]["currentTurn"] = current_actor
        return deepcopy(combat)

    def _turn_state_for_actor(self, actor_id: str) -> dict[str, Any]:
        combat = self._state.get("combat", {})
        existing = combat.get("turnState", {}).get(actor_id)
        if existing:
            return existing
        try:
            character = self.find_character(actor_id)
            speed = int(character.get("speed", 30))
        except ValueError:
            speed = 30
        turn_state = default_turn_state(actor_id)
        turn_state["movementMax"] = speed
        return turn_state

    def _require_turn_state(self, actor_id: str) -> dict[str, Any]:
        combat = self._state["combat"]
        if not combat["active"]:
            raise ValueError("combat is not active")
        if self.current_combat_actor_id() != actor_id:
            raise ValueError(f"it is not {actor_id}'s turn")
        return combat["turnState"].setdefault(actor_id, self._turn_state_for_actor(actor_id))

    def _spend_combat_movement(self, token: dict[str, Any], x: int, y: int) -> None:
        combat = self._state.get("combat", {})
        if not combat.get("active"):
            return
        actor_id = str(token.get("actorId", token["id"]))
        turn_state = self._require_turn_state(actor_id)
        cost = self._movement_cost(token["x"], token["y"], x, y)
        if turn_state["movementUsed"] + cost > turn_state["movementMax"]:
            raise ValueError("movement exceeds remaining speed")
        turn_state["movementUsed"] += cost

    def _movement_cost(self, from_x: int, from_y: int, to_x: int, to_y: int) -> int:
        squares = abs(to_x - from_x) + abs(to_y - from_y)
        cost = squares * 5
        if self.terrain_at(to_x, to_y) == "difficult":
            cost += 5
        return cost

    def _assert_can_change_combatant(self, user_id: str, target_id: str) -> None:
        if self.is_dm(user_id):
            return
        if not self._state["combat"]["active"]:
            self.assert_can_control_character(user_id, target_id)
            return
        actor_id = self.current_combat_actor_id()
        self.assert_can_control_actor(user_id, actor_id)

    def _normalize_spell_slot_level(self, level: int | str) -> str:
        try:
            numeric_level = int(level)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid spell slot level: {level}") from error
        if numeric_level < 1 or numeric_level > 9:
            raise ValueError(f"invalid spell slot level: {level}")
        return str(numeric_level)

    def _normalize_resource_amount(self, amount: int) -> int:
        normalized = int(amount)
        if normalized < 1:
            raise ValueError("resource amount must be at least 1")
        return normalized

    def _find_character_resource(self, character: dict[str, Any], resource_name: str) -> dict[str, Any]:
        normalized = str(resource_name).strip().lower()
        if not normalized:
            raise ValueError("resource name is required")
        for resource in character.get("resources", []):
            if str(resource.get("name", "")).strip().lower() == normalized:
                return resource
        raise ValueError(f"unknown resource for {character['name']}: {resource_name}")

    def _sync_life_conditions(self, character: dict[str, Any]) -> None:
        conditions = [item for item in character.get("conditions", []) if item not in {"dead", "dying", "unconscious"}]
        if character["hp"]["current"] <= 0:
            conditions.append("dying")
            conditions.append("unconscious")
        character["conditions"] = sorted(set(conditions))

    def _find_reaction_window(self, window_id: str) -> dict[str, Any]:
        for window in self._state["combat"]["reactionWindows"]:
            if window["id"] == window_id:
                return window
        raise ValueError(f"unknown reaction window: {window_id}")

    def _find_pending_action(self, action_id: str) -> dict[str, Any]:
        for action in self._state["pendingActions"]:
            if action["id"] == action_id:
                return action
        raise ValueError(f"unknown pending action: {action_id}")

    def _complete_pending(self, action_id: str, status: str) -> None:
        for action in self._state["pendingActions"]:
            if action["id"] == action_id:
                action["status"] = status


def current_time() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%H:%M")


def normalize_token_name(value: str) -> str:
    return value.strip().lower()


def normalize_login_username(value: str) -> str:
    return " ".join(value.strip().lower().split())


def ability_modifier(character: dict[str, Any], ability: str) -> int:
    key = ability.upper()
    ability_detail = character.get("abilities", {}).get(key)
    if isinstance(ability_detail, dict) and "modifier" in ability_detail:
        return int(ability_detail["modifier"])
    return (int(character.get("attributes", {}).get(key, 10)) - 10) // 2


def fresh_default_state() -> dict[str, Any]:
    state = deepcopy(_DEFAULT_STATE)
    state["map"] = map_repository.load_default_map()
    for token in state["tokens"]:
        token.setdefault("actorId", token["id"])
    state["characters"] = [normalize_character_card(character) for character in state["characters"]]
    state["combat"] = default_combat_state()
    state["pendingActions"] = []
    return state


def fresh_adventure_start_state() -> dict[str, Any]:
    state = {
        "session": {
            "id": "demo-dnd-session",
            "title": "凡戴尔的失落矿坑",
            "mode": "character_creation",
            "round": 0,
            "currentTurn": "",
        },
        "adventure": {
            "moduleName": "凡戴尔的失落矿坑",
            "chapter": "冒险准备",
            "scene": "",
            "source": "module",
            "startedAt": "",
        },
        "players": [
            {
                "id": f"player-{index}",
                "displayName": f"Player {index}",
                "characterId": None,
                "role": "player",
                "joined": False,
                "ready": False,
            }
            for index in range(1, 6)
        ] + [{"id": "dm", "displayName": "DM", "characterId": None, "role": "dm", "joined": False, "ready": False}],
        "map": map_repository.validate_map(
            {
                "id": "adventure-start",
                "name": "冒险准备",
                "width": 10,
                "height": 6,
                "gridSize": 48,
                "terrain": [],
                "annotations": [{"x": 4, "y": 2, "label": "队伍集结"}],
            }
        ),
        "tokens": [],
        "characters": [],
        "combat": default_combat_state(),
        "pendingActions": [],
        "events": [
            {
                "type": "system",
                "speaker": "Adventure",
                "text": "玩家加入后先创建角色；准备好后即可从冒险模组开始。",
                "time": current_time(),
            }
        ],
    }
    return state


class _SessionRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._stores: dict[str, GameStateStore] = {DEFAULT_SESSION_ID: GameStateStore()}
        self._tokens: dict[str, SessionToken] = {}
        self._claimed: dict[str, set[str]] = {}
        self._usernames: dict[str, dict[str, str]] = {}

    def get(self, session_id: str = DEFAULT_SESSION_ID) -> GameStateStore:
        with self._lock:
            return self._stores[DEFAULT_SESSION_ID]

    def join(self, *, role: str = "player", username: str, session_id: str = DEFAULT_SESSION_ID) -> SessionToken:
        normalized_role = role.strip().lower()
        if normalized_role not in {"player", "dm"}:
            raise ValueError("role must be player or dm")
        display_name = username.strip()
        normalized_username = normalize_login_username(display_name)
        if not normalized_username:
            raise ValueError("username is required")

        now = datetime.now(timezone.utc)
        with self._lock:
            self._reap_expired_locked(now)
            store = self.get(session_id)
            claimed = self._claimed.setdefault(session_id, set())
            usernames = self._usernames.setdefault(session_id, {})
            players = store.snapshot()["players"]

            user_id = usernames.get(normalized_username)
            if user_id is not None:
                player = self._player_for_user_id(players, user_id)
                if player is None:
                    usernames.pop(normalized_username, None)
                elif player.get("role") != normalized_role:
                    raise PermissionError(f"username is already joined as {player.get('role')}")
                else:
                    return self._issue_token_locked(
                        session_id=session_id,
                        user_id=user_id,
                        role=str(player.get("role", normalized_role)),
                        display_name=display_name,
                        username=normalized_username,
                        claimed=claimed,
                        usernames=usernames,
                        store=store,
                        now=now,
                    )

            for player in players:
                user_id = str(player["id"])
                if player.get("role") != normalized_role or user_id in claimed:
                    continue
                return self._issue_token_locked(
                    session_id=session_id,
                    user_id=user_id,
                    role=str(player.get("role", normalized_role)),
                    display_name=display_name,
                    username=normalized_username,
                    claimed=claimed,
                    usernames=usernames,
                    store=store,
                    now=now,
                )
        raise PermissionError(f"no available {normalized_role} seats")

    def resolve(self, token: str) -> Principal:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._reap_expired_locked(now)
            session_token = self._tokens.get(token)
            if session_token is None:
                raise KeyError("invalid session token")
            if session_token.expires_at <= now:
                self._revoke_locked(token)
                raise KeyError("expired session token")
            return session_token.principal

    def revoke(self, token: str) -> None:
        with self._lock:
            self._revoke_locked(token)

    def reset_auth(self) -> None:
        with self._lock:
            self._tokens.clear()
            self._claimed.clear()
            self._usernames.clear()

    def _issue_token_locked(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        display_name: str,
        username: str,
        claimed: set[str],
        usernames: dict[str, str],
        store: GameStateStore,
        now: datetime,
    ) -> SessionToken:
        self._revoke_user_tokens_locked(session_id, user_id)
        self._forget_usernames_for_user_locked(usernames, user_id)
        claimed.add(user_id)
        usernames[username] = user_id
        store.update_player_presence(user_id, display_name=display_name, joined=True)
        token = secrets.token_urlsafe(32)
        session_token = SessionToken(
            token=token,
            principal=Principal(session_id=session_id, user_id=user_id, role=role),
            expires_at=now + SESSION_TOKEN_TTL,
        )
        self._tokens[token] = session_token
        return session_token

    def _reap_expired_locked(self, now: datetime) -> None:
        for token, session_token in list(self._tokens.items()):
            if session_token.expires_at <= now:
                self._revoke_locked(token)

    def _revoke_locked(self, token: str) -> None:
        session_token = self._tokens.pop(token, None)
        if session_token is None:
            return
        claimed = self._claimed.get(session_token.principal.session_id)
        if claimed is not None:
            claimed.discard(session_token.principal.user_id)
        store = self.get(session_token.principal.session_id)
        store.update_player_presence(session_token.principal.user_id, joined=False, ready=False)

    def _revoke_user_tokens_locked(self, session_id: str, user_id: str) -> None:
        for token, session_token in list(self._tokens.items()):
            principal = session_token.principal
            if principal.session_id == session_id and principal.user_id == user_id:
                self._tokens.pop(token, None)

    def _forget_usernames_for_user_locked(self, usernames: dict[str, str], user_id: str) -> None:
        for username, mapped_user_id in list(usernames.items()):
            if mapped_user_id == user_id:
                usernames.pop(username, None)

    def _player_for_user_id(self, players: list[dict[str, Any]], user_id: str) -> dict[str, Any] | None:
        normalized = normalize_token_name(user_id)
        for player in players:
            if str(player["id"]).lower() == normalized:
                return player
        return None


_registry = _SessionRegistry()


def get_store(session_id: str = DEFAULT_SESSION_ID) -> GameStateStore:
    return _registry.get(session_id)


def join_session(*, role: str = "player", username: str, session_id: str = DEFAULT_SESSION_ID) -> SessionToken:
    return _registry.join(role=role, username=username, session_id=session_id)


def resolve_session_token(token: str) -> Principal:
    return _registry.resolve(token)


def revoke_session_token(token: str) -> None:
    _registry.revoke(token)


def reset_auth() -> None:
    _registry.reset_auth()


game_state = get_store(DEFAULT_SESSION_ID)
