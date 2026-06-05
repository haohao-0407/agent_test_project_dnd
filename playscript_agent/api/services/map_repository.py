from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODULE_NAME = "凡戴尔的失落矿坑"
DEFAULT_MAP_ID = "roadside-ruin"
DEFAULT_MAP_DIR = PROJECT_ROOT / "document" / "modules" / DEFAULT_MODULE_NAME / "maps"
DEFAULT_MAP_PATH = DEFAULT_MAP_DIR / f"{DEFAULT_MAP_ID}.json"
EDITABLE_MAP_FIELDS = {"id", "name", "width", "height", "gridSize", "terrain", "annotations"}


FALLBACK_MAP: dict[str, Any] = {
    "id": DEFAULT_MAP_ID,
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
}


def load_default_map() -> dict[str, Any]:
    return load_map(DEFAULT_MAP_PATH)


def load_map(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return deepcopy(FALLBACK_MAP)
    data = json.loads(source.read_text(encoding="utf-8"))
    return validate_map(data)


def save_default_map(game_map: dict[str, Any]) -> None:
    save_map(DEFAULT_MAP_PATH, game_map)


def save_map(path: str | Path, game_map: dict[str, Any]) -> None:
    validated = validate_map(game_map)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def apply_map_updates(
    current_map: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(updates, dict):
        raise ValueError("map updates must be an object")
    next_map = deepcopy(current_map)
    for key, value in updates.items():
        if key not in EDITABLE_MAP_FIELDS:
            raise ValueError(f"map field cannot be updated: {key}")
        next_map[key] = deepcopy(value)
    return validate_map(next_map)


def validate_map(game_map: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(game_map, dict):
        raise ValueError("map must be an object")

    required = {"id", "name", "width", "height", "gridSize", "terrain", "annotations"}
    missing = required - set(game_map)
    if missing:
        raise ValueError(f"map is missing fields: {', '.join(sorted(missing))}")

    width = _positive_int(game_map["width"], "width")
    height = _positive_int(game_map["height"], "height")
    grid_size = _positive_int(game_map["gridSize"], "gridSize")
    if width > 200 or height > 200:
        raise ValueError("map dimensions cannot exceed 200x200")

    validated = {
        "id": _non_empty_string(game_map["id"], "id"),
        "name": _non_empty_string(game_map["name"], "name"),
        "width": width,
        "height": height,
        "gridSize": grid_size,
        "terrain": _validate_positioned_items(
            game_map["terrain"],
            width=width,
            height=height,
            value_key="type",
            value_name="terrain type",
        ),
        "annotations": _validate_positioned_items(
            game_map["annotations"],
            width=width,
            height=height,
            value_key="label",
            value_name="annotation label",
        ),
    }
    return validated


def _validate_positioned_items(
    items: Any,
    *,
    width: int,
    height: int,
    value_key: str,
    value_name: str,
) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError(f"{value_key} must be a list")

    seen: set[tuple[int, int]] = set()
    validated: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"{value_key} entries must be objects")
        x = _non_negative_int(item.get("x"), "x")
        y = _non_negative_int(item.get("y"), "y")
        if x >= width or y >= height:
            raise ValueError(f"map item ({x}, {y}) is outside the map")
        key = (x, y)
        if key in seen:
            raise ValueError(f"duplicate map item at ({x}, {y})")
        seen.add(key)
        validated.append(
            {
                "x": x,
                "y": y,
                value_key: _non_empty_string(item.get(value_key), value_name),
            }
        )
    return validated


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _non_negative_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
