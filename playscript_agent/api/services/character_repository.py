from __future__ import annotations

import json
import re
from base64 import b64decode
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes

from playscript_agent.api.services.game_state import normalize_character_card


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PERMANENT_CHARACTER_DIR = PROJECT_ROOT / "document" / "characters" / "permanent"
CHARACTER_JSON_NAME = "character.json"
CHARACTER_IMAGE_ROUTE = "/character-assets"


def load_permanent_characters() -> list[dict[str, Any]]:
    if not PERMANENT_CHARACTER_DIR.exists():
        return []

    characters: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for character_path in sorted(PERMANENT_CHARACTER_DIR.glob(f"*/{CHARACTER_JSON_NAME}")):
        data = json.loads(character_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"permanent character file must be an object: {character_path}")
        character = normalize_character_card(data)
        normalized_id = character["id"].lower()
        if normalized_id in seen_ids:
            raise ValueError(f"duplicate permanent character id: {character['id']}")
        seen_ids.add(normalized_id)
        characters.append(character)
    return characters


def create_permanent_character(character: dict[str, Any]) -> dict[str, Any]:
    characters = load_permanent_characters()
    next_character = normalize_character_card(character)
    if any(item["id"].lower() == next_character["id"].lower() for item in characters):
        raise ValueError(f"permanent character already exists: {next_character['id']}")
    write_permanent_character(next_character)
    return deepcopy(next_character)


def update_permanent_character(character_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    for character in load_permanent_characters():
        if character["id"].lower() == character_id.lower():
            next_character = deepcopy(character)
            next_character.update(deepcopy(updates))
            next_character["id"] = character["id"]
            next_character = normalize_character_card(next_character)
            write_permanent_character(next_character)
            return deepcopy(next_character)
    raise ValueError(f"unknown permanent character: {character_id}")


def write_permanent_character(character: dict[str, Any]) -> None:
    normalized = normalize_character_card(character)
    character_dir = permanent_character_dir(normalized["id"])
    character_path = permanent_character_path(normalized["id"])
    character_dir.mkdir(parents=True, exist_ok=True)
    normalized["images"] = write_character_images(character_dir, normalized.get("images", []))
    character_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def permanent_character_path(character_id: str) -> Path:
    return permanent_character_dir(character_id) / CHARACTER_JSON_NAME


def permanent_character_dir(character_id: str) -> Path:
    return PERMANENT_CHARACTER_DIR / safe_character_file_stem(character_id)


def write_character_images(character_dir: Path, images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    images_dir = character_dir / "images"
    normalized_images: list[dict[str, Any]] = []
    expected_files: set[Path] = set()
    for index, image in enumerate(images):
        next_image = deepcopy(image)
        data_url = str(next_image.pop("dataUrl", "") or "")
        image_id = str(next_image.get("id") or f"image-{index + 1}").strip() or f"image-{index + 1}"
        next_image["id"] = image_id

        if data_url:
            decoded = decode_data_url(data_url)
            if decoded is None:
                continue
            mime_type, image_bytes = decoded
            images_dir.mkdir(parents=True, exist_ok=True)
            image_path = images_dir / image_file_name(next_image, mime_type)
            image_path.write_bytes(image_bytes)
            next_image["mimeType"] = mime_type
            next_image["size"] = len(image_bytes)
            next_image["path"] = f"images/{image_path.name}"

        image_path_value = str(next_image.get("path") or "").strip()
        if not image_path_value:
            continue

        image_path = character_dir / image_path_value
        expected_files.add(image_path)
        next_image["url"] = character_asset_url(character_dir, image_path_value)
        normalized_images.append(next_image)

    if images_dir.exists():
        for existing_path in images_dir.glob("*"):
            if existing_path.is_file() and existing_path not in expected_files:
                existing_path.unlink()
    return normalized_images


def decode_data_url(data_url: str) -> tuple[str, bytes] | None:
    if not data_url.startswith("data:") or "," not in data_url:
        return None
    header, payload = data_url.split(",", 1)
    mime_type = header[5:].split(";", 1)[0] or "application/octet-stream"
    if ";base64" in header:
        return mime_type, b64decode(payload)
    return mime_type, unquote_to_bytes(payload)


def image_file_name(image: dict[str, Any], mime_type: str) -> str:
    file_name = str(image.get("fileName") or "").strip()
    suffix = Path(file_name).suffix.lower()
    if not suffix or len(suffix) > 12:
        suffix = image_extension(mime_type)
    return f"{safe_character_file_stem(str(image.get('id') or 'image'))}{suffix}"


def image_extension(mime_type: str) -> str:
    extensions = {
        "image/gif": ".gif",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/svg+xml": ".svg",
        "image/webp": ".webp",
    }
    return extensions.get(mime_type, ".bin")


def character_asset_url(character_dir: Path, relative_path: str) -> str:
    character_folder = character_dir.name
    return f"{CHARACTER_IMAGE_ROUTE}/{character_folder}/{relative_path.replace('\\', '/')}"


def safe_character_file_stem(character_id: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", character_id.strip()).strip("._-")
    return stem or "character"
