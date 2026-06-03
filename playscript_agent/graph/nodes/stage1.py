from __future__ import annotations

from typing import Any, Protocol

from langgraph.types import interrupt

from playscript_agent.graph.state import (
    GameState,
    append_private,
    append_public,
    make_event,
)
from playscript_agent.script import load_script


class DMNarrator(Protocol):
    def opening(self, script: Any) -> str: ...

    def reveal(self, script: Any) -> str: ...


def setup_node(state: GameState) -> dict[str, Any]:
    script = load_script(state["script_root"])
    human_player_id = state["current_speaker"]
    character = next(
        (
            candidate
            for candidate in script.characters
            if candidate.character_id == human_player_id
        ),
        script.characters[0],
    )

    participant = {
        "participant_id": character.character_id,
        "character_id": character.character_id,
        "name": character.name,
        "kind": "human",
    }
    private_profile = make_event(
        kind="private_profile",
        visibility="private",
        speaker="dm",
        content=character.private_profile,
        phase="setup",
        audience=[participant["participant_id"]],
        metadata={"character_id": character.character_id},
    )
    system_event = make_event(
        kind="system",
        visibility="public",
        speaker="system",
        content=f"剧本《{script.meta.title}》已载入，玩家 {character.name} 已入场。",
        phase="setup",
        metadata={"script_id": script.meta.script_id},
    )

    return {
        "script_id": script.meta.script_id,
        "script_title": script.meta.title,
        "phase": "opening",
        "participants": [participant],
        "current_speaker": participant["participant_id"],
        "public_events": append_public(state, system_event),
        "private_events": append_private(state, private_profile),
    }


def make_dm_narrate_node(dm: DMNarrator):
    def dm_narrate_node(state: GameState) -> dict[str, Any]:
        script = load_script(state["script_root"])
        opening = make_event(
            kind="dm",
            visibility="public",
            speaker="dm",
            content=dm.opening(script),
            phase="opening",
        )
        return {
            "phase": "introductions",
            "public_events": append_public(state, opening),
        }

    return dm_narrate_node


def make_human_introduction_node():
    def human_introduction_node(state: GameState) -> dict[str, Any]:
        speaker_id = state["current_speaker"]
        participant = _participant_by_id(state, speaker_id)
        prompt = {
            "type": "player_introduction",
            "participant_id": speaker_id,
            "character_name": participant["name"],
            "prompt": f"请以 {participant['name']} 的身份做一句自我介绍。",
        }
        response = interrupt(prompt)
        text = _resume_text(response)
        intro_event = make_event(
            kind="player",
            visibility="public",
            speaker=speaker_id,
            content=text,
            phase="introductions",
            metadata={"character_id": participant["character_id"]},
        )
        return {
            "phase": "reveal",
            "turn_count": state["turn_count"] + 1,
            "pending_interrupts": [],
            "public_events": append_public(state, intro_event),
        }

    return human_introduction_node


def make_reveal_node(dm: DMNarrator):
    def reveal_node(state: GameState) -> dict[str, Any]:
        script = load_script(state["script_root"])
        reveal = make_event(
            kind="truth",
            visibility="public",
            speaker="dm",
            content=dm.reveal(script),
            phase="reveal",
            metadata={"script_id": script.meta.script_id},
        )
        return {
            "phase": "complete",
            "is_complete": True,
            "public_events": append_public(state, reveal),
        }

    return reveal_node


def _participant_by_id(state: GameState, participant_id: str) -> dict[str, Any]:
    return next(
        participant
        for participant in state["participants"]
        if participant["participant_id"] == participant_id
    )


def _resume_text(response: Any) -> str:
    if isinstance(response, dict):
        value = response.get("text") or response.get("message") or response.get("content")
        if value:
            return str(value)
    return str(response)
