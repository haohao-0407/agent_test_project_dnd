from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from langchain.chat_models import init_chat_model


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "llm.yaml"


def get_llm(role: str, *, config_path: str | Path = DEFAULT_CONFIG) -> Any:
    """Return a LangChain chat model for a role.

    Phase 1 keeps the graph runnable with the offline DeterministicDM, but this
    function establishes the future single-LLM/multi-LLM boundary.
    """

    path = Path(config_path)
    config = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    models = config.get("models", {})
    model_name = models.get(role) or models.get("default")
    if not model_name:
        raise ValueError(f"no LLM configured for role {role!r}")
    return init_chat_model(model_name)
