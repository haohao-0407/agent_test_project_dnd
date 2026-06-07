from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuleAccessContext:
    participant_id: str | None = None
    is_dm: bool = False

    @classmethod
    def for_dm(cls) -> "RuleAccessContext":
        return cls(is_dm=True)

    @classmethod
    def for_player(cls, participant_id: str) -> "RuleAccessContext":
        if not participant_id.strip():
            raise ValueError("participant_id is required for rule access")
        return cls(participant_id=participant_id)


def build_rule_chroma_where_filter(context: RuleAccessContext) -> dict[str, Any]:
    """Build the metadata filter for DND rulebook access.

    Core rules are normally public, while module notes, monster blocks, and
    hidden map notes can be stored as dm_only or character:<id> chunks later.
    """

    if context.is_dm:
        return {}

    return {
        "$or": [
            {"visibility": "public"},
            {"visibility": f"character:{context.participant_id}"},
        ]
    }


def metadata_matches_filter(
    metadata: dict[str, Any],
    where_filter: dict[str, Any],
) -> bool:
    """Small test helper mirroring the subset of Chroma filters we generate."""

    if not where_filter:
        return True
    if "$and" in where_filter:
        return all(metadata_matches_filter(metadata, part) for part in where_filter["$and"])
    if "$or" in where_filter:
        return any(metadata_matches_filter(metadata, part) for part in where_filter["$or"])

    for key, expected in where_filter.items():
        actual = metadata.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$lte" in expected and actual > expected["$lte"]:
                return False
        elif actual != expected:
            return False
    return True
