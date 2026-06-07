from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any
from urllib.parse import quote

from playscript_agent.api.services import monster_repository
from playscript_agent.api.services.game_state import base_character_card, get_store
from playscript_agent.api.services.map_repository import DEFAULT_MODULE_NAME, PROJECT_ROOT, load_map, validate_map
from playscript_agent.llm import get_llm


MODULE_ROOT = PROJECT_ROOT / "document" / "modules"
DEFAULT_MODULE_PATH = MODULE_ROOT / DEFAULT_MODULE_NAME / f"{DEFAULT_MODULE_NAME}.md"
SCENES_FILE_NAME = "scenes.json"


def start_adventure(
    *,
    user_id: str,
    session_id: str = "default",
    module_name: str = DEFAULT_MODULE_NAME,
) -> dict[str, Any]:
    module_text = load_module_text(module_name)
    party = _party_summary(session_id)
    scene = load_opening_scene(module_name)
    if scene is None:
        scene = generate_opening_scene(module_text, party=party, module_name=module_name)
    scene["openingText"] = generate_opening_narration(
        module_text,
        scene=scene,
        party=party,
        module_name=module_name,
    )
    return get_store(session_id).start_adventure(
        user_id=user_id,
        module_name=module_name,
        game_map=scene["map"],
        monsters=scene["monsters"],
        opening_text=scene["openingText"],
        source=scene["source"],
        exploration_scene_id=scene.get("explorationSceneId", ""),
        exploration_scene_name=scene.get("explorationSceneName", ""),
        background_url=scene.get("backgroundUrl", ""),
        combat_scene_id=scene.get("combatSceneId", ""),
        combat_scene_name=scene.get("combatSceneName", ""),
    )


def prepare_combat_scene(
    *,
    session_id: str = "default",
    scene_id: str | None = None,
    user_id: str = "dm",
) -> dict[str, Any]:
    store = get_store(session_id)
    state = store.snapshot()
    adventure = state.get("adventure", {})
    module_name = str(adventure.get("moduleName") or DEFAULT_MODULE_NAME)
    target_scene_id = scene_id or adventure.get("combatSceneId")
    if not str(target_scene_id or "").strip():
        raise ValueError("combat scene id is required")
    collection = load_scene_collection(module_name)
    linked_exploration_scene = _find_linked_exploration_scene(collection, str(target_scene_id or ""))
    combat_scene = load_combat_scene(module_name, str(target_scene_id or ""))
    if combat_scene is None:
        raise ValueError(f"unknown combat scene: {target_scene_id}")
    chapter = str(linked_exploration_scene.get("chapter") or combat_scene.get("chapter") or adventure.get("chapter") or "") if linked_exploration_scene else str(combat_scene.get("chapter") or adventure.get("chapter") or "")
    return store.set_combat_scene(
        game_map=combat_scene["map"],
        monsters=combat_scene["monsters"],
        combat_scene_id=combat_scene["combatSceneId"],
        combat_scene_name=combat_scene["combatSceneName"],
        user_id=user_id,
        module_name=module_name,
        chapter=chapter,
        exploration_scene_id=str(linked_exploration_scene.get("id") or "") if linked_exploration_scene else None,
        exploration_scene_name=str(linked_exploration_scene.get("name") or "") if linked_exploration_scene else None,
        background_url=module_asset_url(module_name, str(linked_exploration_scene.get("background") or "")) if linked_exploration_scene else None,
    )


def load_module_text(module_name: str = DEFAULT_MODULE_NAME) -> str:
    path = MODULE_ROOT / module_name / f"{module_name}.md"
    if not path.exists():
        path = DEFAULT_MODULE_PATH
    return path.read_text(encoding="utf-8")


def load_scene_collection(module_name: str = DEFAULT_MODULE_NAME) -> dict[str, Any] | None:
    path = MODULE_ROOT / module_name / SCENES_FILE_NAME
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("module scenes file must be an object")
    return data


def load_opening_scene(module_name: str = DEFAULT_MODULE_NAME) -> dict[str, Any] | None:
    collection = load_scene_collection(module_name)
    if collection is None:
        return None
    opening_scene_id = str(collection.get("openingSceneId") or "")
    exploration_scene = _find_scene(collection.get("explorationScenes", []), opening_scene_id)
    if exploration_scene is None:
        return None
    combat_scene_id = str(exploration_scene.get("battleSceneId") or "")
    combat_scene = _combat_scene_from_collection(module_name, collection, combat_scene_id)
    if combat_scene is None:
        return None
    return {
        **combat_scene,
        "openingText": str(exploration_scene.get("openingText") or ""),
        "source": "module",
        "moduleName": module_name,
        "explorationSceneId": str(exploration_scene.get("id") or opening_scene_id),
        "explorationSceneName": str(exploration_scene.get("name") or ""),
        "backgroundUrl": module_asset_url(module_name, str(exploration_scene.get("background") or "")),
        "scenePrompt": str(exploration_scene.get("scenePrompt") or exploration_scene.get("openingText") or ""),
    }


def load_combat_scene(module_name: str, scene_id: str) -> dict[str, Any] | None:
    collection = load_scene_collection(module_name)
    if collection is None:
        return None
    return _combat_scene_from_collection(module_name, collection, scene_id)


def scene_browser(module_name: str = DEFAULT_MODULE_NAME) -> dict[str, Any]:
    collection = load_scene_collection(module_name)
    if collection is None:
        return {
            "moduleName": module_name,
            "openingSceneId": "",
            "explorationScenes": [],
            "combatScenes": [],
        }
    combat_scenes = [
        scene
        for scene in collection.get("combatScenes", [])
        if isinstance(scene, dict)
    ]
    combat_by_id = {str(scene.get("id") or ""): scene for scene in combat_scenes}
    linked_exploration_ids: dict[str, list[str]] = {}
    exploration_scenes = [
        scene
        for scene in collection.get("explorationScenes", [])
        if isinstance(scene, dict)
    ]
    for scene in exploration_scenes:
        combat_scene_id = str(scene.get("combatSceneId") or scene.get("battleSceneId") or "")
        if combat_scene_id:
            linked_exploration_ids.setdefault(combat_scene_id, []).append(str(scene.get("id") or ""))
    return {
        "moduleName": str(collection.get("moduleName") or module_name),
        "version": str(collection.get("version") or ""),
        "openingSceneId": str(collection.get("openingSceneId") or ""),
        "explorationScenes": [
            _exploration_scene_summary(module_name, scene, combat_by_id)
            for scene in exploration_scenes
        ],
        "combatScenes": [
            _combat_scene_summary(scene, linked_exploration_ids.get(str(scene.get("id") or ""), []))
            for scene in combat_scenes
        ],
    }


def switch_exploration_scene(
    *,
    user_id: str,
    session_id: str = "default",
    module_name: str = DEFAULT_MODULE_NAME,
    scene_id: str,
) -> dict[str, Any]:
    scene = load_exploration_scene(module_name, scene_id)
    if scene is None:
        raise ValueError(f"unknown exploration scene: {scene_id}")
    combat_scene = scene.get("combatScene")
    store = get_store(session_id)
    state = store.set_exploration_scene(
        user_id=user_id,
        module_name=module_name,
        chapter=str(scene.get("chapter") or ""),
        exploration_scene_id=str(scene.get("id") or scene_id),
        exploration_scene_name=str(scene.get("name") or ""),
        background_url=str(scene.get("backgroundUrl") or ""),
        combat_scene_id=str(combat_scene.get("id") or "") if isinstance(combat_scene, dict) else "",
        combat_scene_name=str(combat_scene.get("name") or "") if isinstance(combat_scene, dict) else "",
    )
    store.append_event(
        {
            "type": "system",
            "speaker": "Adventure",
            "text": f"Scene changed to {scene.get('name') or scene_id}.",
        }
    )
    return store.snapshot()


def load_exploration_scene(module_name: str, scene_id: str) -> dict[str, Any] | None:
    collection = load_scene_collection(module_name)
    if collection is None:
        return None
    scene = _find_scene(collection.get("explorationScenes", []), scene_id, fallback_to_first=False)
    if scene is None:
        return None
    combat_scene_id = str(scene.get("combatSceneId") or scene.get("battleSceneId") or "")
    combat_scene = _find_scene(collection.get("combatScenes", []), combat_scene_id, fallback_to_first=False)
    return _exploration_scene_summary(
        module_name,
        scene,
        {combat_scene_id: combat_scene} if combat_scene is not None else {},
    )


def module_asset_url(module_name: str, relative_path: str) -> str:
    if not relative_path:
        return ""
    encoded_module = quote(module_name.replace("\\", "/").strip("/"))
    encoded_path = "/".join(quote(part) for part in relative_path.replace("\\", "/").strip("/").split("/"))
    return f"/module-assets/{encoded_module}/{encoded_path}"


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


def scene_collection_summary(module_name: str = DEFAULT_MODULE_NAME) -> dict[str, Any]:
    collection = load_scene_collection(module_name)
    if collection is None:
        return {"explorationScenes": [], "combatScenes": []}
    return {
        "explorationScenes": [
            {
                "id": scene.get("id"),
                "name": scene.get("name"),
                "battleSceneId": scene.get("battleSceneId"),
            }
            for scene in collection.get("explorationScenes", [])
            if isinstance(scene, dict)
        ],
        "combatScenes": [
            {
                "id": scene.get("id"),
                "name": scene.get("name"),
                "trigger": scene.get("trigger"),
            }
            for scene in collection.get("combatScenes", [])
            if isinstance(scene, dict)
        ],
    }


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


def generate_opening_narration(
    module_text: str,
    *,
    scene: dict[str, Any],
    party: list[dict[str, str]],
    module_name: str,
) -> str:
    intro_excerpt = _module_intro_excerpt_from_text(module_text)
    scene_prompt = str(scene.get("scenePrompt") or scene.get("openingText") or "")
    try:
        llm = get_llm("dm")
        response = llm.invoke(
            [
                (
                    "system",
                    "You are a Chinese DND Dungeon Master beginning a published adventure in exploration mode. "
                    "First introduce the adventure according to the DM guidance, module introduction, background, overview, and adventure hook. "
                    "Do not jump directly into the first encounter, battle map, dead horses, ambush, or tactical scene. "
                    "Frame why the party is together, what their patron or hook asks of them, and invite players to introduce their characters, relationships, marching order, and motivations. "
                    "Use the characters' race/class/background details when they naturally color the moment. "
                    "Do not start combat yet; end with a clear prompt for character introductions and how they accept or personalize the adventure hook. "
                    "Keep it vivid, concise, and player-facing. Do not mention JSON, tools, or hidden notes.",
                ),
                (
                    "human",
                    json.dumps(
                        {
                            "moduleName": module_name,
                            "party": party,
                            "explorationScene": {
                                "id": scene.get("explorationSceneId"),
                                "name": scene.get("explorationSceneName"),
                                "laterScenePromptDoNotNarrateYet": scene_prompt,
                                "backgroundUrl": scene.get("backgroundUrl"),
                                "linkedCombatSceneId": scene.get("combatSceneId"),
                            },
                            "moduleIntroAndDmGuidanceExcerpt": intro_excerpt,
                        },
                        ensure_ascii=False,
                    ),
                ),
            ]
        )
        content = getattr(response, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass
    return _fallback_opening_narration(scene=scene, party=party)


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
        "explorationSceneId": "fallback-opening",
        "explorationSceneName": "冒险开场",
        "backgroundUrl": module_asset_url(module_name, "pictures/Player/triboar-trail-exploration.png"),
        "scenePrompt": "根据当前模组开场与玩家角色信息自由演绎开场，不要直接进入战斗。",
        "combatSceneId": "triboar-trail-ambush",
        "combatSceneName": "三猪小径伏击",
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
            "explorationSceneId": "llm-opening",
            "explorationSceneName": "冒险开场",
            "backgroundUrl": module_asset_url(module_name, "pictures/Player/triboar-trail-exploration.png"),
            "scenePrompt": "根据 LLM 生成的开场战斗场景和玩家角色信息自由演绎开场，不要直接进入战斗。",
            "combatSceneId": str(game_map.get("id") or "llm-combat-scene"),
            "combatSceneName": str(game_map.get("name") or "战斗场景"),
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


def _module_intro_excerpt_from_text(text: str) -> str:
    end = text.find("# 地精箭矢")
    if end < 0:
        end = text.find("### 地精伏击")
    if end < 0:
        end = min(len(text), 8000)
    intro = text[:end].strip()
    if len(intro) > 8000:
        background = text.find("### 背景")
        if background >= 0 and background < end:
            intro = text[:2500] + "\n\n" + text[background:end]
    return intro.strip()[:8000]


def _extract_json(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    return match.group(0) if match else stripped


def _fallback_opening_narration(*, scene: dict[str, Any], party: list[dict[str, str]]) -> str:
    party_names = "、".join(character["name"] for character in party if character.get("name"))
    if not party_names:
        party_names = "冒险者们"
    party_detail = "；".join(
        " ".join(
            item
            for item in [
                character.get("name", ""),
                character.get("race", ""),
                character.get("class", ""),
                character.get("background", ""),
            ]
            if item
        )
        for character in party
    )
    role_note = f"队伍中有 {party_detail}。" if party_detail else ""
    return (
        f"{party_names}的故事从一份前往凡达林的委托开始。"
        f"{role_note}矮人刚铎·寻岩者需要一支可靠队伍护送补给前往边境小镇，"
        "而他对自己新发现的秘密显得兴奋又谨慎。"
        "在启程前，请介绍你们的角色、你们如何认识刚铎，"
        "以及你们为什么愿意接下这趟看似普通却暗藏风险的旅程。"
    )


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
                    "background": character.get("background", ""),
                    "level": str(character.get("level", "")),
                }
            )
    return party


def _find_scene(scenes: Any, scene_id: str, *, fallback_to_first: bool = True) -> dict[str, Any] | None:
    if not isinstance(scenes, list):
        return None
    if scene_id:
        for scene in scenes:
            if isinstance(scene, dict) and str(scene.get("id") or "") == scene_id:
                return scene
        if not fallback_to_first:
            return None
    if not fallback_to_first:
        return None
    for scene in scenes:
        if isinstance(scene, dict):
            return scene
    return None


def _find_linked_exploration_scene(collection: dict[str, Any] | None, combat_scene_id: str) -> dict[str, Any] | None:
    if collection is None:
        return None
    for scene in collection.get("explorationScenes", []):
        if not isinstance(scene, dict):
            continue
        if str(scene.get("combatSceneId") or scene.get("battleSceneId") or "") == combat_scene_id:
            return scene
    return None


def _exploration_scene_summary(
    module_name: str,
    scene: dict[str, Any],
    combat_by_id: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    combat_scene_id = str(scene.get("combatSceneId") or scene.get("battleSceneId") or "")
    combat_scene = combat_by_id.get(combat_scene_id)
    return {
        "id": str(scene.get("id") or ""),
        "name": str(scene.get("name") or ""),
        "chapter": str(scene.get("chapter") or ""),
        "kind": str(scene.get("kind") or ""),
        "background": str(scene.get("background") or ""),
        "backgroundUrl": module_asset_url(module_name, str(scene.get("background") or "")),
        "scenePrompt": str(scene.get("scenePrompt") or ""),
        "combatSceneId": combat_scene_id,
        "combatScene": _combat_scene_summary(combat_scene, []) if isinstance(combat_scene, dict) else None,
    }


def _combat_scene_summary(scene: dict[str, Any] | None, linked_exploration_scene_ids: list[str]) -> dict[str, Any] | None:
    if scene is None:
        return None
    monsters = scene.get("monsters", [])
    return {
        "id": str(scene.get("id") or ""),
        "name": str(scene.get("name") or ""),
        "chapter": str(scene.get("chapter") or ""),
        "map": str(scene.get("map") or ""),
        "trigger": str(scene.get("trigger") or ""),
        "monsterCount": len(monsters) if isinstance(monsters, list) else 0,
        "linkedExplorationSceneIds": linked_exploration_scene_ids,
    }


def _combat_scene_from_collection(
    module_name: str,
    collection: dict[str, Any],
    scene_id: str,
) -> dict[str, Any] | None:
    scene = _find_scene(collection.get("combatScenes", []), scene_id, fallback_to_first=False)
    if scene is None:
        return None
    map_path = MODULE_ROOT / module_name / str(scene.get("map") or "")
    monsters = [
        _normalize_monster(
            {
                **monster,
                "character": _monster(
                    str(monster.get("id") or "monster"),
                    str(monster.get("name") or "Monster"),
                    int(monster.get("x", 0)),
                    int(monster.get("y", 0)),
                )["character"],
            }
        )
        for monster in scene.get("monsters", [])
        if isinstance(monster, dict)
    ]
    return {
        "map": load_map(map_path),
        "monsters": monsters,
        "combatSceneId": str(scene.get("id") or scene_id),
        "combatSceneName": str(scene.get("name") or ""),
    }


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
    bestiary_character = monster_repository.bestiary_character_by_name(name, character_id=monster_id)
    if bestiary_character is not None:
        return {"id": monster_id, "name": name, "x": x, "y": y, "character": bestiary_character}

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
