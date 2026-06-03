from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal


ContentType = Literal[
    "background",
    "clue",
    "character_profile",
    "truth",
    "dm_manual",
]

VALID_CONTENT_TYPES: set[str] = {
    "background",
    "clue",
    "character_profile",
    "truth",
    "dm_manual",
}

PUBLIC_VISIBILITY = "public"
DM_ONLY_VISIBILITY = "dm_only"
CHARACTER_VISIBILITY_PREFIX = "character:"


class SchemaError(ValueError):
    """Raised when a script file violates the stage-0 data contract."""


@dataclass(frozen=True, slots=True)
class ScriptMeta:
    script_id: str
    title: str
    min_players: int
    max_players: int
    phases: tuple[str, ...]
    synopsis: str = ""

    def __post_init__(self) -> None:
        require_non_empty("script_id", self.script_id)
        require_non_empty("title", self.title)
        if self.min_players < 1:
            raise SchemaError("min_players must be >= 1")
        if self.max_players < self.min_players:
            raise SchemaError("max_players must be >= min_players")
        if not self.phases:
            raise SchemaError("phases must contain at least one phase")


@dataclass(frozen=True, slots=True)
class Character:
    character_id: str
    name: str
    public_profile: str
    private_profile: str

    def __post_init__(self) -> None:
        require_non_empty("character_id", self.character_id)
        require_non_empty("name", self.name)
        require_non_empty("public_profile", self.public_profile)
        require_non_empty("private_profile", self.private_profile)


@dataclass(frozen=True, slots=True)
class ScriptChunk:
    chunk_id: str
    content_type: ContentType
    title: str
    content: str
    visibility: str
    phase: int
    clue_id: str | None = None
    source: str = ""

    def __post_init__(self) -> None:
        require_non_empty("chunk_id", self.chunk_id)
        require_non_empty("title", self.title)
        require_non_empty("content", self.content)
        if self.content_type not in VALID_CONTENT_TYPES:
            raise SchemaError(f"unsupported content_type: {self.content_type}")
        validate_visibility(self.visibility)
        if self.phase < 0:
            raise SchemaError("phase must be >= 0")
        if self.clue_id is not None:
            require_non_empty("clue_id", self.clue_id)

    def chroma_metadata(self) -> dict[str, str | int]:
        """Return metadata with a stable sentinel for non-clue chunks."""

        return {
            "chunk_id": self.chunk_id,
            "type": self.content_type,
            "visibility": self.visibility,
            "phase": self.phase,
            "clue_id": self.clue_id or "",
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ScriptBundle:
    meta: ScriptMeta
    characters: tuple[Character, ...]
    chunks: tuple[ScriptChunk, ...]

    def __post_init__(self) -> None:
        if not self.characters:
            raise SchemaError("script must define at least one character")
        if not self.chunks:
            raise SchemaError("script must define at least one chunk")

        character_ids = [character.character_id for character in self.characters]
        ensure_unique("character_id", character_ids)
        ensure_unique("chunk_id", [chunk.chunk_id for chunk in self.chunks])

        known_characters = set(character_ids)
        for chunk in self.chunks:
            owner = character_visibility_owner(chunk.visibility)
            if owner and owner not in known_characters:
                raise SchemaError(
                    f"chunk {chunk.chunk_id!r} references unknown character {owner!r}"
                )

        clue_ids = [chunk.clue_id for chunk in self.chunks if chunk.clue_id]
        ensure_unique("clue_id", clue_ids)


@dataclass(frozen=True, slots=True)
class AccessContext:
    participant_id: str | None
    current_phase: int
    revealed_clues: frozenset[str] = field(default_factory=frozenset)
    is_dm: bool = False

    @classmethod
    def for_dm(cls) -> "AccessContext":
        return cls(participant_id=None, current_phase=0, is_dm=True)

    @classmethod
    def for_player(
        cls,
        participant_id: str,
        current_phase: int,
        revealed_clues: Iterable[str] = (),
    ) -> "AccessContext":
        require_non_empty("participant_id", participant_id)
        return cls(
            participant_id=participant_id,
            current_phase=current_phase,
            revealed_clues=frozenset(revealed_clues),
        )

    def __post_init__(self) -> None:
        if self.current_phase < 0:
            raise SchemaError("current_phase must be >= 0")
        if not self.is_dm and not self.participant_id:
            raise SchemaError("participant_id is required for non-DM access")


def require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field_name} must be a non-empty string")


def validate_visibility(value: str) -> None:
    require_non_empty("visibility", value)
    if value in {PUBLIC_VISIBILITY, DM_ONLY_VISIBILITY}:
        return
    if value.startswith(CHARACTER_VISIBILITY_PREFIX):
        owner = value.removeprefix(CHARACTER_VISIBILITY_PREFIX)
        require_non_empty("character visibility owner", owner)
        return
    raise SchemaError(
        "visibility must be 'public', 'dm_only', or 'character:<character_id>'"
    )


def character_visibility_owner(value: str) -> str | None:
    if value.startswith(CHARACTER_VISIBILITY_PREFIX):
        return value.removeprefix(CHARACTER_VISIBILITY_PREFIX)
    return None


def ensure_unique(field_name: str, values: Iterable[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise SchemaError(f"duplicate {field_name}: {value}")
        seen.add(value)


def require_keys(data: dict[str, Any], keys: Iterable[str], source: str) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise SchemaError(f"{source} missing required keys: {', '.join(missing)}")
