from __future__ import annotations

import argparse
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from playscript_agent.graph import build_game_graph, create_initial_state
from playscript_agent.graph.state import Event, GameState


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the stage-1 demo game.")
    parser.add_argument(
        "--script-root",
        default=str(Path(__file__).resolve().parents[2] / "scripts" / "demo"),
        help="Path to a folder-based script.",
    )
    parser.add_argument("--player-id", default="lin_an")
    parser.add_argument("--thread-id", default=f"demo-{uuid4()}")
    parser.add_argument(
        "--auto-intro",
        default=None,
        help="Provide introduction text without interactive input.",
    )
    args = parser.parse_args()

    app = build_game_graph()
    config = {"configurable": {"thread_id": args.thread_id}}
    state = create_initial_state(
        script_root=args.script_root,
        human_player_id=args.player_id,
        thread_id=args.thread_id,
    )

    result = app.invoke(state, config)
    _print_new_public_events([], result)

    interrupts = result.get("__interrupt__", [])
    if interrupts:
        prompt = interrupts[0].value
        print(f"\n[等待输入] {prompt['prompt']}")
        answer = args.auto_intro
        if answer is None:
            answer = input("> ")
        before_events = result["public_events"]
        result = app.invoke(Command(resume=answer), config)
        _print_new_public_events(before_events, result)

    if result.get("is_complete"):
        print("\n[结束] 阶段 1 demo 已完成。")


def _print_new_public_events(previous: list[Event], state: GameState) -> None:
    previous_ids = {event["event_id"] for event in previous}
    for event in state["public_events"]:
        if event["event_id"] not in previous_ids:
            print(f"\n[{event['speaker']}:{event['kind']}]\n{event['content']}")


if __name__ == "__main__":
    main()
