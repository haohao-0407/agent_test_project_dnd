from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from playscript_agent.agents.dm import DeterministicDM
from playscript_agent.graph.nodes import (
    make_dm_narrate_node,
    make_human_introduction_node,
    make_reveal_node,
    setup_node,
)
from playscript_agent.graph.state import GameState


def build_game_graph(*, dm: DeterministicDM | None = None, checkpointer=None):
    narrator = dm or DeterministicDM()
    graph = StateGraph(GameState)
    graph.add_node("setup", setup_node)
    graph.add_node("dm_narrate", make_dm_narrate_node(narrator))
    graph.add_node("introductions", make_human_introduction_node())
    graph.add_node("reveal", make_reveal_node(narrator))

    graph.add_edge(START, "setup")
    graph.add_edge("setup", "dm_narrate")
    graph.add_edge("dm_narrate", "introductions")
    graph.add_edge("introductions", "reveal")
    graph.add_edge("reveal", END)

    return graph.compile(checkpointer=checkpointer or InMemorySaver())
