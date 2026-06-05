from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
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
        },
        {
            "id": "player-mira",
            "displayName": "Mira Player",
            "characterId": "mira",
            "role": "player",
        },
        {
            "id": "dm",
            "displayName": "DM",
            "characterId": None,
            "role": "dm",
        },
    ],
    "map": map_repository.load_default_map(),
    "tokens": [
        {"id": "kael", "name": "Kael", "kind": "player", "x": 2, "y": 3},
        {"id": "mira", "name": "Mira", "kind": "player", "x": 3, "y": 4},
        {"id": "goblin-1", "name": "Goblin", "kind": "monster", "x": 8, "y": 3},
        {"id": "wolf-1", "name": "Wolf", "kind": "monster", "x": 9, "y": 5},
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
    ],
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
        self._state = fresh_default_state()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def reset(self) -> None:
        with self._lock:
            self._state = fresh_default_state()

    def append_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            event.setdefault("time", current_time())
            self._state["events"].append(event)
            self._state["events"] = self._state["events"][-80:]

    def move_token(self, token_id: str, x: int, y: int) -> dict[str, Any]:
        with self._lock:
            if not self.is_in_bounds(x, y):
                raise ValueError("target square is outside the map")
            if self.terrain_at(x, y) == "wall":
                raise ValueError("target square is blocked")
            token = self.find_token(token_id)
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
            return deepcopy(next_character)

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

    def find_token(self, token_id_or_name: str) -> dict[str, Any]:
        normalized = normalize_token_name(token_id_or_name)
        for token in self._state["tokens"]:
            if token["id"].lower() == normalized or token["name"].lower() == normalized:
                return token
        raise ValueError(f"unknown token: {token_id_or_name}")

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

    def _assert_tokens_fit_map(self, game_map: dict[str, Any]) -> None:
        wall_squares = {
            (terrain["x"], terrain["y"])
            for terrain in game_map["terrain"]
            if terrain["type"] == "wall"
        }
        for token in self._state["tokens"]:
            x = token["x"]
            y = token["y"]
            if not (0 <= x < game_map["width"] and 0 <= y < game_map["height"]):
                raise ValueError(f"map update would leave token {token['id']} outside the map")
            if (x, y) in wall_squares:
                raise ValueError(f"map update would place a wall under token {token['id']}")


def current_time() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%H:%M")


def normalize_token_name(value: str) -> str:
    return value.strip().lower()


def fresh_default_state() -> dict[str, Any]:
    state = deepcopy(_DEFAULT_STATE)
    state["map"] = map_repository.load_default_map()
    state["characters"] = [normalize_character_card(character) for character in state["characters"]]
    return state


game_state = GameStateStore()
