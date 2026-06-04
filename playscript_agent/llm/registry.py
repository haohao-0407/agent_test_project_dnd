from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "llm.yaml"


def get_llm(role: str, *, config_path: str | Path = DEFAULT_CONFIG) -> Any:
    """Return a LangChain chat model for a role.

    Phase 1 keeps the graph runnable with the offline DeterministicDM, but this
    function establishes the future single-LLM/multi-LLM boundary.
    """

    load_dotenv()
    path = Path(config_path)
    config = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    model_name, kwargs = resolve_llm_config(role, config, os.environ)
    if not model_name:
        raise ValueError(f"no LLM configured for role {role!r}")
    return init_chat_model(model_name, **kwargs)


def resolve_llm_config(
    role: str,
    config: Mapping[str, Any],
    env: Mapping[str, str],
) -> tuple[str, dict[str, Any]]:
    """Resolve role config into init_chat_model(model, **kwargs).

    Supported shapes:

    ```yaml
    models:
      dm: "anthropic:claude-sonnet-4-5"
      player:
        model: "openai:gpt-4o-mini"
        api_key_env: OPENAI_API_KEY
        base_url_env: OPENAI_BASE_URL
        temperature: 0.7
        kwargs:
          timeout: 30
    ```
    """

    models = config.get("models", {})
    raw = models.get(role) or models.get("default")
    if raw is None:
        return "", {}
    if isinstance(raw, str):
        return _resolve_env_reference(raw, env), {}
    if not isinstance(raw, Mapping):
        raise TypeError(f"LLM config for role {role!r} must be a string or mapping")

    model_name = _resolve_env_reference(str(raw.get("model", "")), env)
    kwargs: dict[str, Any] = {}

    model_provider = _resolved_optional(raw.get("model_provider"), env)
    if model_provider:
        kwargs["model_provider"] = model_provider

    api_key = _value_from_direct_or_env(raw, "api_key", "api_key_env", env)
    if api_key:
        kwargs["api_key"] = api_key

    base_url = _value_from_direct_or_env(raw, "base_url", "base_url_env", env)
    if base_url:
        kwargs["base_url"] = base_url

    extra_kwargs = raw.get("kwargs", {})
    if extra_kwargs:
        if not isinstance(extra_kwargs, Mapping):
            raise TypeError(f"LLM kwargs for role {role!r} must be a mapping")
        kwargs.update(_resolve_mapping_values(extra_kwargs, env))

    reserved = {
        "model",
        "model_provider",
        "api_key",
        "api_key_env",
        "base_url",
        "base_url_env",
        "kwargs",
    }
    passthrough = {
        key: value
        for key, value in raw.items()
        if key not in reserved and _resolved_optional(value, env) is not None
    }
    kwargs.update(_resolve_mapping_values(passthrough, env))
    return model_name, kwargs


def _value_from_direct_or_env(
    data: Mapping[str, Any],
    direct_key: str,
    env_key: str,
    env: Mapping[str, str],
) -> str | None:
    direct = _resolved_optional(data.get(direct_key), env)
    if direct:
        return str(direct)
    variable = data.get(env_key)
    if not variable:
        return None
    return env.get(str(variable)) or None


def _resolve_mapping_values(
    data: Mapping[str, Any],
    env: Mapping[str, str],
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in data.items():
        resolved_value = _resolved_optional(value, env)
        if resolved_value is not None:
            resolved[key] = resolved_value
    return resolved


def _resolved_optional(value: Any, env: Mapping[str, str]) -> Any | None:
    if value is None:
        return None
    if isinstance(value, str):
        resolved = _resolve_env_reference(value, env).strip()
        return resolved or None
    return value


def _resolve_env_reference(value: str, env: Mapping[str, str]) -> str:
    stripped = value.strip()
    if stripped.startswith("${") and stripped.endswith("}"):
        return env.get(stripped[2:-1], "")
    if stripped.startswith("$") and len(stripped) > 1:
        return env.get(stripped[1:], "")
    return value
