from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playscript_agent.script.schema import (
    CHARACTER_VISIBILITY_PREFIX,
    Character,
    ContentType,
    DM_ONLY_VISIBILITY,
    PUBLIC_VISIBILITY,
    ScriptBundle,
    ScriptChunk,
    ScriptMeta,
    require_keys,
)


def load_script(root: str | Path) -> ScriptBundle:
    """Load the stage-0 folder-based script format."""

    script_root = Path(root)
    meta = _load_meta(script_root / "meta.json")
    characters = _load_characters(script_root / "characters")
    chunks: list[ScriptChunk] = []

    chunks.append(
        ScriptChunk(
            chunk_id="background:public",
            content_type="background",
            title="公开背景",
            content=(script_root / "background.md").read_text(encoding="utf-8"),
            visibility=PUBLIC_VISIBILITY,
            phase=0,
            source="background.md",
        )
    )

    for character in characters:
        chunks.append(
            ScriptChunk(
                chunk_id=f"character:{character.character_id}:public",
                content_type="character_profile",
                title=f"{character.name}公开身份",
                content=character.public_profile,
                visibility=PUBLIC_VISIBILITY,
                phase=0,
                source=f"characters/{character.character_id}.json",
            )
        )
        chunks.append(
            ScriptChunk(
                chunk_id=f"character:{character.character_id}:private",
                content_type="character_profile",
                title=f"{character.name}私密剧本",
                content=character.private_profile,
                visibility=f"{CHARACTER_VISIBILITY_PREFIX}{character.character_id}",
                phase=0,
                source=f"characters/{character.character_id}.json",
            )
        )

    chunks.extend(_load_clues(script_root / "clues.json"))
    chunks.extend(_load_truth(script_root / "truth.json"))
    chunks.extend(_load_dm_manual(script_root / "dm_manual.json"))

    return ScriptBundle(
        meta=meta,
        characters=tuple(characters),
        chunks=tuple(chunks),
    )


def _load_meta(path: Path) -> ScriptMeta:
    data = _read_json_object(path)
    require_keys(
        data,
        ["script_id", "title", "min_players", "max_players", "phases"],
        str(path),
    )
    return ScriptMeta(
        script_id=data["script_id"],
        title=data["title"],
        min_players=int(data["min_players"]),
        max_players=int(data["max_players"]),
        phases=tuple(data["phases"]),
        synopsis=data.get("synopsis", ""),
    )


def _load_characters(root: Path) -> list[Character]:
    characters: list[Character] = []
    for path in sorted(root.glob("*.json")):
        data = _read_json_object(path)
        require_keys(
            data,
            ["character_id", "name", "public_profile", "private_profile"],
            str(path),
        )
        characters.append(
            Character(
                character_id=data["character_id"],
                name=data["name"],
                public_profile=data["public_profile"],
                private_profile=data["private_profile"],
            )
        )
    return characters


def _load_clues(path: Path) -> list[ScriptChunk]:
    clues = _read_json_array(path)
    chunks: list[ScriptChunk] = []
    for clue in clues:
        require_keys(
            clue,
            ["clue_id", "title", "content", "visibility", "phase"],
            str(path),
        )
        clue_id = clue["clue_id"]
        chunks.append(
            ScriptChunk(
                chunk_id=f"clue:{clue_id}",
                content_type="clue",
                title=clue["title"],
                content=clue["content"],
                visibility=clue["visibility"],
                phase=int(clue["phase"]),
                clue_id=clue_id,
                source="clues.json",
            )
        )
    return chunks


def _load_truth(path: Path) -> list[ScriptChunk]:
    data = _read_json_object(path)
    require_keys(data, ["title", "content"], str(path))
    return [
        ScriptChunk(
            chunk_id="truth:solution",
            content_type="truth",
            title=data["title"],
            content=data["content"],
            visibility=DM_ONLY_VISIBILITY,
            phase=int(data.get("phase", 0)),
            source="truth.json",
        )
    ]


def _load_dm_manual(path: Path) -> list[ScriptChunk]:
    manual = _read_json_array(path)
    chunks: list[ScriptChunk] = []
    for index, item in enumerate(manual, start=1):
        require_keys(item, ["title", "content"], str(path))
        chunks.append(
            ScriptChunk(
                chunk_id=f"dm_manual:{index}",
                content_type="dm_manual",
                title=item["title"],
                content=item["content"],
                visibility=DM_ONLY_VISIBILITY,
                phase=int(item.get("phase", 0)),
                source="dm_manual.json",
            )
        )
    return chunks


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(f"{path} must contain a JSON array")
    return data
