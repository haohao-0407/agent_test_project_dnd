from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict
from uuid import uuid4


PhaseName = Literal["setup", "opening", "introductions", "reveal", "complete"]
EventVisibility = Literal["public", "private"]
EventKind = Literal[
    "system",
    "dm",
    "player",
    "clue",
    "truth",
    "private_profile",
]
ParticipantKind = Literal["human", "ai"]


class Event(TypedDict):
    event_id: str
    kind: EventKind
    visibility: EventVisibility
    speaker: str
    content: str
    phase: PhaseName
    audience: list[str]
    created_at: str
    metadata: dict[str, Any]


class Participant(TypedDict):
    participant_id: str
    character_id: str
    name: str
    kind: ParticipantKind


class PendingInterrupt(TypedDict):
    interrupt_id: str
    participant_id: str
    prompt: str
    phase: PhaseName


class GameState(TypedDict):
    thread_id: str
    session_id: str
    script_root: str
    script_id: str
    script_title: str
    phase: PhaseName
    public_events: list[Event]
    private_events: list[Event]
    revealed_clues: list[str]
    votes: dict[str, str]
    participants: list[Participant]
    current_speaker: str
    pending_interrupts: list[PendingInterrupt]
    turn_count: int
    phase_deadline: str | None
    summaries: dict[str, str]
    is_complete: bool


def create_initial_state(
    *,
    script_root: str,
    human_player_id: str,
    thread_id: str | None = None,
    session_id: str | None = None,
) -> GameState:
    return {
        "thread_id": thread_id or f"thread-{uuid4()}",
        "session_id": session_id or f"session-{uuid4()}",
        "script_root": script_root,
        "script_id": "",
        "script_title": "",
        "phase": "setup",
        "public_events": [],
        "private_events": [],
        "revealed_clues": [],
        "votes": {},
        "participants": [],
        "current_speaker": human_player_id,
        "pending_interrupts": [],
        "turn_count": 0,
        "phase_deadline": None,
        "summaries": {},
        "is_complete": False,
    }


def make_event(
    *,
    kind: EventKind,
    visibility: EventVisibility,
    speaker: str,
    content: str,
    phase: PhaseName,
    audience: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Event:
    return {
        "event_id": f"event-{uuid4()}",
        "kind": kind,
        "visibility": visibility,
        "speaker": speaker,
        "content": content,
        "phase": phase,
        "audience": audience or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }


def append_public(state: GameState, *events: Event) -> list[Event]:
    return [*state["public_events"], *events]


def append_private(state: GameState, *events: Event) -> list[Event]:
    return [*state["private_events"], *events]
