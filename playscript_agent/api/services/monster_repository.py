from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from playscript_agent.api.services.game_state import ABILITY_KEYS, base_character_card, normalize_character_card


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PERMANENT_MONSTER_DIR = PROJECT_ROOT / "document" / "characters" / "permanent-monsters"
MONSTER_BESTIARY_CSV = PROJECT_ROOT / "document" / "rules" / "怪物图鉴.csv"
MONSTER_JSON_NAME = "monster.json"

MONSTER_TEXT_FIELDS = {
    "source": "",
    "page": "",
    "size": "",
    "type": "",
    "alignment": "",
    "armorClass": "10",
    "hitPoints": "1",
    "speed": "30 尺",
    "savingThrows": "",
    "skills": "",
    "damageVulnerabilities": "",
    "damageResistances": "",
    "damageImmunities": "",
    "conditionImmunities": "",
    "senses": "",
    "languages": "",
    "challengeRating": "",
    "traits": "",
    "actions": "",
    "bonusActions": "",
    "reactions": "",
    "legendaryActions": "",
    "mythicActions": "",
    "lairActions": "",
    "regionalEffects": "",
    "environment": "",
    "treasure": "",
    "notes": "",
}
MONSTER_EDITABLE_FIELDS = {"id", "name", "attributes", *MONSTER_TEXT_FIELDS.keys()}


def load_permanent_monsters() -> list[dict[str, Any]]:
    if not PERMANENT_MONSTER_DIR.exists():
        return []

    monsters: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for monster_path in sorted(PERMANENT_MONSTER_DIR.glob(f"*/{MONSTER_JSON_NAME}")):
        data = json.loads(monster_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"permanent monster file must be an object: {monster_path}")
        monster = normalize_monster_card(data)
        normalized_id = monster["id"].lower()
        if normalized_id in seen_ids:
            raise ValueError(f"duplicate permanent monster id: {monster['id']}")
        seen_ids.add(normalized_id)
        monsters.append(monster)
    return monsters


def create_permanent_monster(monster: dict[str, Any]) -> dict[str, Any]:
    monsters = load_permanent_monsters()
    next_monster = normalize_monster_card(monster)
    if any(item["id"].lower() == next_monster["id"].lower() for item in monsters):
        raise ValueError(f"permanent monster already exists: {next_monster['id']}")
    write_permanent_monster(next_monster)
    return deepcopy(next_monster)


def update_permanent_monster(monster_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    for monster in load_permanent_monsters():
        if monster["id"].lower() == monster_id.lower():
            next_monster = deepcopy(monster)
            for key, value in updates.items():
                if key not in MONSTER_EDITABLE_FIELDS or key == "id":
                    raise ValueError(f"monster field cannot be updated: {key}")
                next_monster[key] = deepcopy(value)
            next_monster["id"] = monster["id"]
            next_monster = normalize_monster_card(next_monster)
            write_permanent_monster(next_monster)
            return deepcopy(next_monster)
    raise ValueError(f"unknown permanent monster: {monster_id}")


def write_permanent_monster(monster: dict[str, Any]) -> None:
    normalized = normalize_monster_card(monster)
    monster_dir = permanent_monster_dir(normalized["id"])
    monster_dir.mkdir(parents=True, exist_ok=True)
    permanent_monster_path(normalized["id"]).write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def permanent_monster_path(monster_id: str) -> Path:
    return permanent_monster_dir(monster_id) / MONSTER_JSON_NAME


def permanent_monster_dir(monster_id: str) -> Path:
    return PERMANENT_MONSTER_DIR / safe_monster_file_stem(monster_id)


def normalize_monster_card(raw_monster: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_monster, dict):
        raise ValueError("monster must be an object")
    monster_id = str(raw_monster.get("id") or raw_monster.get("name") or "monster").strip()
    name = str(raw_monster.get("name") or monster_id).strip()
    if not monster_id or not name:
        raise ValueError("monster id and name are required")

    normalized: dict[str, Any] = {"id": monster_id, "name": name, **deepcopy(MONSTER_TEXT_FIELDS)}
    for key in MONSTER_TEXT_FIELDS:
        normalized[key] = str(raw_monster.get(key) or MONSTER_TEXT_FIELDS[key]).strip()
    normalized["attributes"] = {
        key: int_value((raw_monster.get("attributes") or {}).get(key, 10), default=10)
        for key in ABILITY_KEYS
    }
    return normalized


def bestiary_monster_by_name(name: str) -> dict[str, Any] | None:
    normalized_name = normalize_lookup_name(name)
    if not normalized_name or not MONSTER_BESTIARY_CSV.exists():
        return None
    with MONSTER_BESTIARY_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_name = str(row.get("名称") or "").strip()
            if normalize_lookup_name(row_name) == normalized_name:
                return monster_from_bestiary_row(row)
    return None


def monster_from_bestiary_row(row: dict[str, str]) -> dict[str, Any]:
    name = str(row.get("名称") or "monster").strip()
    return normalize_monster_card(
        {
            "id": safe_monster_file_stem(name),
            "name": name,
            "source": row.get("来源", ""),
            "page": row.get("页码", ""),
            "size": row.get("体型", ""),
            "type": row.get("类型", ""),
            "alignment": row.get("阵营", ""),
            "armorClass": row.get("AC", ""),
            "hitPoints": row.get("HP", ""),
            "speed": row.get("速度", ""),
            "attributes": {
                "STR": row.get("力量", 10),
                "DEX": row.get("敏捷", 10),
                "CON": row.get("体质", 10),
                "INT": row.get("智力", 10),
                "WIS": row.get("感知", 10),
                "CHA": row.get("魅力", 10),
            },
            "savingThrows": row.get("豁免骰", ""),
            "skills": row.get("技能", ""),
            "damageVulnerabilities": row.get("伤害易伤", ""),
            "damageResistances": row.get("伤害抗性", ""),
            "damageImmunities": row.get("伤害免疫", ""),
            "conditionImmunities": row.get("状态免疫", ""),
            "senses": row.get("感官", ""),
            "languages": row.get("语言", ""),
            "challengeRating": row.get("CR", ""),
            "traits": row.get("特质", ""),
            "actions": row.get("动作", ""),
            "bonusActions": row.get("附赠动作", ""),
            "reactions": row.get("反应", ""),
            "legendaryActions": row.get("传奇动作", ""),
            "mythicActions": row.get("神话动作", ""),
            "lairActions": row.get("巢穴动作", ""),
            "regionalEffects": row.get("区域效应", ""),
            "environment": row.get("环境", ""),
            "treasure": row.get("宝藏", ""),
        }
    )


def monster_to_character_card(monster: dict[str, Any], *, character_id: str | None = None) -> dict[str, Any]:
    normalized = normalize_monster_card(monster)
    combat_id = character_id or normalized["id"]
    character = base_character_card(combat_id, normalized["name"])
    hp = parse_leading_int(normalized["hitPoints"], default=1)
    character.update(
        {
            "class": "Monster",
            "race": " / ".join(part for part in [normalized["size"], normalized["type"]] if part),
            "alignment": normalized["alignment"] or "Unaligned",
            "hp": {"current": hp, "max": hp, "temp": 0},
            "ac": parse_leading_int(normalized["armorClass"], default=10),
            "initiative": (normalized["attributes"]["DEX"] - 10) // 2,
            "speed": parse_leading_int(normalized["speed"], default=30),
            "attributes": normalized["attributes"],
            "savingThrows": split_stat_text(normalized["savingThrows"]),
            "skills": split_stat_text(normalized["skills"]),
            "attacks": split_action_names(normalized["actions"]),
            "actions": split_action_names(normalized["actions"]),
            "actionDetails": action_details(normalized),
            "defenses": {
                "resistances": split_stat_text(normalized["damageResistances"]),
                "immunities": split_stat_text(normalized["damageImmunities"]),
                "vulnerabilities": split_stat_text(normalized["damageVulnerabilities"]),
            },
            "senses": {
                "passivePerception": parse_passive_perception(normalized["senses"]),
                "passiveInvestigation": 10,
                "passiveInsight": 10,
                "other": split_stat_text(normalized["senses"]),
            },
            "languages": split_stat_text(normalized["languages"]),
            "features": split_action_names(normalized["traits"]),
            "featureDetails": feature_details(normalized["traits"], "特质"),
            "notes": monster_note(normalized),
        }
    )
    return normalize_character_card(character)


def bestiary_character_by_name(name: str, *, character_id: str | None = None) -> dict[str, Any] | None:
    monster = bestiary_monster_by_name(name)
    if monster is None:
        return None
    return monster_to_character_card(monster, character_id=character_id)


def parse_leading_int(value: str, *, default: int) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else default


def int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_passive_perception(senses: str) -> int:
    match = re.search(r"被动察觉\s*(\d+)", senses)
    return int(match.group(1)) if match else 10


def split_stat_text(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text or text in {"—", "-"}:
        return []
    return [item.strip() for item in re.split(r"[，,;；/、]+", text) if item.strip()]


def split_action_names(value: str) -> list[str]:
    details = feature_details(value, "动作")
    return [detail["name"] for detail in details] or split_stat_text(value)


def action_details(monster: dict[str, Any]) -> list[dict[str, str]]:
    sections = [
        ("action", monster["actions"]),
        ("bonus action", monster["bonusActions"]),
        ("reaction", monster["reactions"]),
        ("legendary action", monster["legendaryActions"]),
        ("mythic action", monster["mythicActions"]),
        ("lair action", monster["lairActions"]),
    ]
    details: list[dict[str, str]] = []
    for cost, text in sections:
        for detail in feature_details(text, cost):
            details.append({"name": detail["name"], "cost": cost, "description": detail["description"]})
    return details


def feature_details(value: str, source: str) -> list[dict[str, str]]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", str(value or "").strip()) if block.strip()]
    details: list[dict[str, str]] = []
    for block in blocks:
        first_line = block.splitlines()[0].strip()
        name = first_line.split(".", 1)[0].strip() if "." in first_line else first_line[:30].strip()
        details.append({"name": name or source, "source": source, "description": block})
    return details


def monster_note(monster: dict[str, Any]) -> str:
    lines = [
        f"来源: {monster['source']} {monster['page']}".strip(),
        f"CR: {monster['challengeRating']}".strip(),
        f"状态免疫: {monster['conditionImmunities']}".strip(),
        f"环境: {monster['environment']}".strip(),
        f"宝藏: {monster['treasure']}".strip(),
        monster["notes"],
    ]
    return "\n".join(line for line in lines if line and not line.endswith(":"))


def normalize_lookup_name(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def safe_monster_file_stem(monster_id: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]+", "-", monster_id.strip()).strip("._-")
    return stem or "monster"
