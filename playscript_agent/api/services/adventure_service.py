from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from playscript_agent.api.services.game_state import base_character_card, get_store
from playscript_agent.api.services.map_repository import DEFAULT_MODULE_NAME, PROJECT_ROOT, validate_map
from playscript_agent.llm import get_llm


MODULE_ROOT = PROJECT_ROOT / "document" / "modules"
DEFAULT_MODULE_PATH = MODULE_ROOT / DEFAULT_MODULE_NAME / f"{DEFAULT_MODULE_NAME}.md"


def start_adventure(
    *,
    user_id: str,
    session_id: str = "default",
    module_name: str = DEFAULT_MODULE_NAME,
) -> dict[str, Any]:
    module_text = load_module_text(module_name)
    party = _party_summary(session_id)
    scene = generate_opening_scene(module_text, party=party, module_name=module_name)
    return get_store(session_id).start_adventure(
        user_id=user_id,
        module_name=module_name,
        game_map=scene["map"],
        monsters=scene["monsters"],
        opening_text=scene["openingText"],
        source=scene["source"],
    )


def load_module_text(module_name: str = DEFAULT_MODULE_NAME) -> str:
    path = MODULE_ROOT / module_name / f"{module_name}.md"
    if not path.exists():
        path = DEFAULT_MODULE_PATH
    return path.read_text(encoding="utf-8")


def opening_module_excerpt(module_name: str = DEFAULT_MODULE_NAME) -> str:
    text = load_module_text(module_name)
    start = text.find("# 地精箭矢")
    if start < 0:
        start = text.find("### 冒险引子")
    if start < 0:
        return text[:3500]
    end = text.find("### 地精踪迹", start)
    if end < 0:
        end = start + 5000
    return text[start:end].strip()[:5000]


def generate_opening_scene(
    module_text: str,
    *,
    party: list[dict[str, str]],
    module_name: str,
) -> dict[str, Any]:
    excerpt = _opening_excerpt_from_text(module_text)
    llm_scene = _generate_scene_with_llm(excerpt, party=party, module_name=module_name)
    if llm_scene is not None:
        return llm_scene
    return fallback_opening_scene(module_name=module_name)


def fallback_opening_scene(*, module_name: str = DEFAULT_MODULE_NAME) -> dict[str, Any]:
    game_map = validate_map(
        {
            "id": "triboar-trail-ambush",
            "name": "三猪小径伏击",
            "width": 14,
            "height": 10,
            "gridSize": 48,
            "terrain": [
                *[{"x": x, "y": y, "type": "difficult"} for x in range(14) for y in (0, 1, 8, 9)],
                *[{"x": x, "y": y, "type": "difficult"} for x in (0, 1, 12, 13) for y in range(2, 8)],
            ],
            "annotations": [
                {"x": 7, "y": 4, "label": "死马"},
                {"x": 8, "y": 4, "label": "黑羽箭"},
                {"x": 2, "y": 6, "label": "货车"},
                {"x": 5, "y": 2, "label": "北侧灌木"},
                {"x": 10, "y": 7, "label": "南侧灌木"},
            ],
            "layers": {
                "terrain": [
                    *[{"x": x, "y": y, "type": "difficult"} for x in range(14) for y in (0, 1, 8, 9)],
                    *[{"x": x, "y": y, "type": "difficult"} for x in (0, 1, 12, 13) for y in range(2, 8)],
                ],
                "walls": [],
                "doors": [],
                "obstacles": [{"x": 7, "y": 4, "type": "obstacle"}, {"x": 8, "y": 4, "type": "obstacle"}],
                "annotations": [
                    {"x": 7, "y": 4, "label": "死马"},
                    {"x": 8, "y": 4, "label": "黑羽箭"},
                    {"x": 2, "y": 6, "label": "货车"},
                    {"x": 5, "y": 2, "label": "北侧灌木"},
                    {"x": 10, "y": 7, "label": "南侧灌木"},
                ],
                "fog": [],
                "effects": [],
                "dmNotes": [
                    {"id": "hook", "x": 7, "y": 4, "text": "靠近死马或调查鞍囊时，地精伏击可能爆发。"}
                ],
            },
        }
    )
    return {
        "map": game_map,
        "monsters": [
            _monster("goblin-1", "Goblin", 5, 1),
            _monster("goblin-2", "Goblin", 10, 1),
            _monster("goblin-3", "Goblin", 5, 8),
            _monster("goblin-4", "Goblin", 10, 8),
        ],
        "openingText": (
            "你们护送着刚铎·寻岩者委托的补给车，沿三猪小径向凡达林前进。"
            "道路在林间转弯，两匹插满黑羽箭的死马挡住前路，鞍囊被翻得凌乱，"
            "林地两侧安静得不太自然。"
        ),
        "source": "fallback",
        "moduleName": module_name,
    }


def _generate_scene_with_llm(
    excerpt: str,
    *,
    party: list[dict[str, str]],
    module_name: str,
) -> dict[str, Any] | None:
    try:
        llm = get_llm("dm")
        response = llm.invoke(
            [
                (
                    "system",
                    "You convert DND adventure module text into a playable JSON grid map. "
                    "Return only JSON with keys map, monsters, and openingText. "
                    "Map must have id, name, width, height, gridSize, terrain, annotations, and optional layers. "
                    "Use 0-based coordinates. Keep width <= 20 and height <= 16. "
                    "Terrain types must be wall, water, or difficult. Monsters need id, name, x, y, and character.",
                ),
                (
                    "human",
                    json.dumps(
                        {
                            "moduleName": module_name,
                            "party": party,
                            "openingModuleText": excerpt,
                        },
                        ensure_ascii=False,
                    ),
                ),
            ]
        )
    except Exception:
        return None

    content = getattr(response, "content", "")
    if not isinstance(content, str):
        return None
    try:
        payload = json.loads(_extract_json(content))
        game_map = validate_map(payload["map"])
        monsters = [_normalize_monster(monster) for monster in payload.get("monsters", [])]
        opening_text = str(payload.get("openingText") or "").strip()
        if not opening_text or not monsters:
            return None
        return {
            "map": game_map,
            "monsters": monsters,
            "openingText": opening_text,
            "source": "llm",
            "moduleName": module_name,
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _opening_excerpt_from_text(text: str) -> str:
    start = text.find("# 地精箭矢")
    if start < 0:
        start = text.find("### 冒险引子")
    if start < 0:
        return text[:5000]
    end = text.find("### 地精踪迹", start)
    if end < 0:
        end = start + 6000
    return text[start:end].strip()[:6000]


def _extract_json(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    return match.group(0) if match else stripped


def _party_summary(session_id: str) -> list[dict[str, str]]:
    state = get_store(session_id).snapshot()
    characters = {character["id"]: character for character in state["characters"]}
    party: list[dict[str, str]] = []
    for player in state["players"]:
        character = characters.get(str(player.get("characterId") or ""))
        if player.get("role") == "player" and character:
            party.append(
                {
                    "id": character["id"],
                    "name": character["name"],
                    "race": character.get("race", ""),
                    "class": character.get("class", ""),
                }
            )
    return party


def _normalize_monster(monster: dict[str, Any]) -> dict[str, Any]:
    monster_id = str(monster.get("id") or monster.get("character", {}).get("id") or "monster").strip()
    name = str(monster.get("name") or monster.get("character", {}).get("name") or monster_id).strip()
    character = deepcopy(monster.get("character") or {})
    character.setdefault("id", monster_id)
    character.setdefault("name", name)
    return {
        "id": monster_id,
        "name": name,
        "x": int(monster.get("x", 0)),
        "y": int(monster.get("y", 0)),
        "character": character,
    }


def _monster(monster_id: str, name: str, x: int, y: int) -> dict[str, Any]:
    character = base_character_card(monster_id, name)
    character.update(
        {
            "class": "Monster",
            "race": name,
            "hp": {"current": 7, "max": 7, "temp": 0},
            "ac": 15,
            "initiative": 2,
            "speed": 30,
            "attributes": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
            "skills": ["Stealth"],
            "attacks": ["Scimitar +4 1d6+2", "Shortbow +4 1d6+2"],
        }
    )
    return {"id": monster_id, "name": name, "x": x, "y": y, "character": character}
