from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from playscript_agent.api.services.game_state import normalize_character_card


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PERMANENT_CHARACTER_PATH = PROJECT_ROOT / "document" / "characters" / "permanent-characters.json"


def load_permanent_characters() -> list[dict[str, Any]]:
    if not PERMANENT_CHARACTER_PATH.exists():
        return []
    data = json.loads(PERMANENT_CHARACTER_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("permanent character library must be a list")
    return [normalize_character_card(character) for character in data]


def save_permanent_characters(characters: list[dict[str, Any]]) -> None:
    normalized = [normalize_character_card(character) for character in characters]
    PERMANENT_CHARACTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERMANENT_CHARACTER_PATH.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def create_permanent_character(character: dict[str, Any]) -> dict[str, Any]:
    characters = load_permanent_characters()
    next_character = normalize_character_card(character)
    if any(item["id"].lower() == next_character["id"].lower() for item in characters):
        raise ValueError(f"permanent character already exists: {next_character['id']}")
    characters.append(next_character)
    save_permanent_characters(characters)
    return deepcopy(next_character)


def update_permanent_character(character_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    characters = load_permanent_characters()
    for index, character in enumerate(characters):
        if character["id"].lower() == character_id.lower():
            next_character = deepcopy(character)
            next_character.update(deepcopy(updates))
            next_character["id"] = character["id"]
            next_character = normalize_character_card(next_character)
            characters[index] = next_character
            save_permanent_characters(characters)
            return deepcopy(next_character)
    raise ValueError(f"unknown permanent character: {character_id}")
