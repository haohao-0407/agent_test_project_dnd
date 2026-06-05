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
EDITABLE_MAP_FIELDS = {
    "id",
    "name",
    "width",
    "height",
    "gridSize",
    "terrain",
    "annotations",
    "background",
    "grid",
    "layers",
}


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

    required = {"id", "name", "width", "height", "gridSize"}
    missing = required - set(game_map)
    if missing:
        raise ValueError(f"map is missing fields: {', '.join(sorted(missing))}")

    width = _positive_int(game_map["width"], "width")
    height = _positive_int(game_map["height"], "height")
    grid_size = _positive_int(game_map["gridSize"], "gridSize")
    if width > 200 or height > 200:
        raise ValueError("map dimensions cannot exceed 200x200")

    layers = _normalize_layers(game_map, width=width, height=height)
    terrain = _validate_positioned_items(
        layers["terrain"],
        width=width,
        height=height,
        value_key="type",
        value_name="terrain type",
        allow_duplicates=False,
    )
    annotations = _validate_positioned_items(
        layers["annotations"],
        width=width,
        height=height,
        value_key="label",
        value_name="annotation label",
        allow_duplicates=False,
    )
    layers["terrain"] = terrain
    layers["annotations"] = annotations
    layers["walls"] = _validate_positioned_items(
        layers["walls"],
        width=width,
        height=height,
        value_key="type",
        value_name="wall type",
        allow_duplicates=False,
        default_value="wall",
    )
    layers["doors"] = _validate_positioned_items(
        layers["doors"],
        width=width,
        height=height,
        value_key="type",
        value_name="door type",
        allow_duplicates=False,
        default_value="door",
    )
    layers["obstacles"] = _validate_positioned_items(
        layers["obstacles"],
        width=width,
        height=height,
        value_key="type",
        value_name="obstacle type",
        allow_duplicates=False,
        default_value="obstacle",
    )
    layers["fog"] = _validate_positioned_items(
        layers["fog"],
        width=width,
        height=height,
        value_key="visibility",
        value_name="fog visibility",
        allow_duplicates=False,
        default_value="hidden",
    )
    layers["effects"] = _validate_layer_objects(layers["effects"], width=width, height=height)
    layers["dmNotes"] = _validate_layer_objects(layers["dmNotes"], width=width, height=height)

    validated = {
        "id": _non_empty_string(game_map["id"], "id"),
        "name": _non_empty_string(game_map["name"], "name"),
        "width": width,
        "height": height,
        "gridSize": grid_size,
        "background": _validate_background(game_map.get("background")),
        "grid": _validate_grid(game_map.get("grid"), grid_size=grid_size),
        "layers": layers,
    }
    # Compatibility fields for the existing API and frontend.
    validated["terrain"] = deepcopy(terrain)
    validated["annotations"] = deepcopy(annotations)
    return validated


def _normalize_layers(game_map: dict[str, Any], *, width: int, height: int) -> dict[str, Any]:
    raw_layers = game_map.get("layers")
    if raw_layers is not None and not isinstance(raw_layers, dict):
        raise ValueError("layers must be an object")
    layers = deepcopy(raw_layers or {})
    terrain = game_map.get("terrain", layers.get("terrain", []))
    annotations = game_map.get("annotations", layers.get("annotations", []))
    return {
        "terrain": terrain,
        "walls": layers.get("walls", _wall_layer_from_terrain(terrain)),
        "doors": layers.get("doors", []),
        "obstacles": layers.get("obstacles", []),
        "annotations": annotations,
        "fog": layers.get("fog", []),
        "effects": layers.get("effects", []),
        "dmNotes": layers.get("dmNotes", []),
    }


def _wall_layer_from_terrain(terrain: Any) -> list[dict[str, Any]]:
    if not isinstance(terrain, list):
        return []
    return [
        {"x": item.get("x"), "y": item.get("y"), "type": "wall"}
        for item in terrain
        if isinstance(item, dict) and item.get("type") == "wall"
    ]


def _validate_background(value: Any) -> dict[str, Any]:
    if value is None:
        return {"url": "", "width": 0, "height": 0, "opacity": 1.0}
    if not isinstance(value, dict):
        raise ValueError("background must be an object")
    opacity = value.get("opacity", 1.0)
    if not isinstance(opacity, int | float) or opacity < 0 or opacity > 1:
        raise ValueError("background opacity must be between 0 and 1")
    return {
        "url": str(value.get("url") or "").strip(),
        "width": max(0, int(value.get("width") or 0)),
        "height": max(0, int(value.get("height") or 0)),
        "opacity": float(opacity),
    }


def _validate_grid(value: Any, *, grid_size: int) -> dict[str, Any]:
    if value is None:
        return {"size": grid_size, "originX": 0, "originY": 0, "scale": 1.0, "offsetX": 0, "offsetY": 0}
    if not isinstance(value, dict):
        raise ValueError("grid must be an object")
    scale = value.get("scale", 1.0)
    if not isinstance(scale, int | float) or scale <= 0:
        raise ValueError("grid scale must be positive")
    return {
        "size": _positive_int(value.get("size", grid_size), "grid size"),
        "originX": int(value.get("originX", 0)),
        "originY": int(value.get("originY", 0)),
        "scale": float(scale),
        "offsetX": int(value.get("offsetX", 0)),
        "offsetY": int(value.get("offsetY", 0)),
    }


def _validate_positioned_items(
    items: Any,
    *,
    width: int,
    height: int,
    value_key: str,
    value_name: str,
    allow_duplicates: bool,
    default_value: str | None = None,
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
        if not allow_duplicates and key in seen:
            raise ValueError(f"duplicate map item at ({x}, {y})")
        seen.add(key)
        value = item.get(value_key, default_value)
        validated.append(
            {
                "x": x,
                "y": y,
                value_key: _non_empty_string(value, value_name),
            }
        )
    return validated


def _validate_layer_objects(items: Any, *, width: int, height: int) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError("layer entries must be a list")
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("layer entries must be objects")
        next_item = deepcopy(item)
        if "x" in next_item:
            x = _non_negative_int(next_item["x"], "x")
            if x >= width:
                raise ValueError(f"map item ({x}, {next_item.get('y', 0)}) is outside the map")
            next_item["x"] = x
        if "y" in next_item:
            y = _non_negative_int(next_item["y"], "y")
            if y >= height:
                raise ValueError(f"map item ({next_item.get('x', 0)}, {y}) is outside the map")
            next_item["y"] = y
        next_item.setdefault("id", f"layer-item-{index + 1}")
        validated.append(next_item)
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
