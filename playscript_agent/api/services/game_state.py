from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any


_DEFAULT_STATE: dict[str, Any] = {
    "session": {
        "id": "demo-dnd-session",
        "title": "Ash Frontier",
        "mode": "exploration",
        "round": 1,
        "currentTurn": "kael",
    },
    "map": {
        "id": "roadside-ruin",
        "name": "Roadside Ruin",
        "width": 12,
        "height": 8,
        "gridSize": 48,
        "terrain": [
            {"x": 4, "y": 1, "type": "wall"},
            {"x": 5, "y": 1, "type": "wall"},
            {"x": 6, "y": 1, "type": "wall"},
            {"x": 4, "y": 2, "type": "wall"},
            {"x": 7, "y": 2, "type": "wall"},
            {"x": 2, "y": 5, "type": "water"},
            {"x": 3, "y": 5, "type": "water"},
            {"x": 9, "y": 4, "type": "difficult"},
            {"x": 10, "y": 4, "type": "difficult"},
        ],
        "annotations": [
            {"x": 6, "y": 3, "label": "door"},
            {"x": 10, "y": 6, "label": "firelight"},
        ],
    },
    "tokens": [
        {"id": "kael", "name": "Kael", "kind": "player", "x": 2, "y": 3},
        {"id": "mira", "name": "Mira", "kind": "player", "x": 3, "y": 4},
        {"id": "goblin-1", "name": "Goblin", "kind": "monster", "x": 8, "y": 3},
        {"id": "wolf-1", "name": "Wolf", "kind": "monster", "x": 9, "y": 5},
    ],
    "characters": [
        {
            "id": "kael",
            "name": "Kael",
            "class": "Fighter 3",
            "race": "Human",
            "hp": {"current": 24, "max": 30, "temp": 0},
            "ac": 17,
            "speed": 30,
            "attributes": {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 11, "CHA": 9},
            "skills": ["Athletics", "Intimidation", "Perception"],
            "attacks": ["Longsword +5 1d8+3", "Shortbow +3 1d6+1"],
            "conditions": [],
        },
        {
            "id": "mira",
            "name": "Mira",
            "class": "Wizard 3",
            "race": "High Elf",
            "hp": {"current": 15, "max": 18, "temp": 0},
            "ac": 13,
            "speed": 30,
            "attributes": {"STR": 8, "DEX": 14, "CON": 12, "INT": 17, "WIS": 13, "CHA": 11},
            "skills": ["Arcana", "Investigation", "History"],
            "attacks": ["Fire Bolt +5 1d10", "Dagger +4 1d4+2"],
            "conditions": ["concentrating"],
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
        self._state = deepcopy(_DEFAULT_STATE)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def reset(self) -> None:
        with self._lock:
            self._state = deepcopy(_DEFAULT_STATE)

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

    def find_token(self, token_id_or_name: str) -> dict[str, Any]:
        normalized = normalize_token_name(token_id_or_name)
        for token in self._state["tokens"]:
            if token["id"].lower() == normalized or token["name"].lower() == normalized:
                return token
        raise ValueError(f"unknown token: {token_id_or_name}")

    def is_in_bounds(self, x: int, y: int) -> bool:
        game_map = self._state["map"]
        return 0 <= x < game_map["width"] and 0 <= y < game_map["height"]

    def terrain_at(self, x: int, y: int) -> str | None:
        for terrain in self._state["map"]["terrain"]:
            if terrain["x"] == x and terrain["y"] == y:
                return terrain["type"]
        return None


def current_time() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%H:%M")


def normalize_token_name(value: str) -> str:
    return value.strip().lower()


game_state = GameStateStore()
