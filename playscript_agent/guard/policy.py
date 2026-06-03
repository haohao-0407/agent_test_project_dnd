from __future__ import annotations

from collections.abc import Iterable

from playscript_agent.script.schema import (
    AccessContext,
    DM_ONLY_VISIBILITY,
    PUBLIC_VISIBILITY,
    ScriptChunk,
)


def can_view_chunk(chunk: ScriptChunk, context: AccessContext) -> bool:
    if context.is_dm:
        return True
    if chunk.phase > context.current_phase:
        return False
    if chunk.clue_id and chunk.clue_id not in context.revealed_clues:
        return False
    if chunk.visibility == PUBLIC_VISIBILITY:
        return True
    if chunk.visibility == DM_ONLY_VISIBILITY:
        return False
    return chunk.visibility == f"character:{context.participant_id}"


def filter_visible_chunks(
    chunks: Iterable[ScriptChunk],
    context: AccessContext,
) -> list[ScriptChunk]:
    return [chunk for chunk in chunks if can_view_chunk(chunk, context)]


def filter_hidden_chunks(
    chunks: Iterable[ScriptChunk],
    context: AccessContext,
) -> list[ScriptChunk]:
    return [chunk for chunk in chunks if not can_view_chunk(chunk, context)]
