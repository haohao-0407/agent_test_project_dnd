# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A D&D 5e tabletop web app. A Python/FastAPI backend holds authoritative game
state and drives an LLM Dungeon Master via tool calls; a React/Vite frontend
renders the battle map, character sheets, chat, dice, and combat panels. A RAG
layer over the 5e rulebook and adventure modules feeds rules context into DM
replies. UI text and DM narration are in Chinese; code and identifiers are English.

## Commands

Backend (run from repo root; `pyproject.toml` sets `pythonpath = ["."]`):

```bash
pip install -r requirements.txt
python -m playscript_agent.api.app --host 127.0.0.1 --port 8766   # serve API + built frontend
pytest                                                            # all tests (testpaths=tests)
pytest tests/test_dnd_api_services.py                             # single file
pytest tests/test_dnd_api_services.py::test_name                  # single test
```

Frontend (run from `web/`):

```bash
npm install
npm run dev        # Vite dev server on 127.0.0.1:5173
npm run build      # tsc typecheck + vite build
```

On Windows, `start_services.bat` launches both backend (8766) and frontend
(5173) in separate windows; `stop_services.bat` kills whatever listens on those
ports.

In dev, Vite (5173) proxies `/api`, `/static`, and `/character-assets` to the
backend (8766) — see `web/vite.config.ts`. In production the backend serves the
built frontend from `playscript_agent/web/static`, so a `npm run build` output
must be copied there for the single-server deployment to show the UI.

## Architecture

### Authoritative state lives in the backend

`api/services/game_state.py` is the heart of the app. A single module-level
`game_state = GameStateStore()` singleton holds the entire game (session, players,
tokens, characters, combat, map, events, pending actions) behind an `RLock`. All
mutating methods take a `user_id` and enforce permissions internally:

- DM (`role == "dm"`) can do anything; players can only act on the character they
  own (`ownerUserId` / `players[].characterId`).
- `assert_can_control_character`, `assert_can_control_actor`,
  `can_roll_for_actor`, and `_assert_can_change_combatant` are the gatekeepers.
  Combat narrows player writes further to the actor whose turn it currently is.

Because state is an in-memory singleton, it resets on backend restart (except the
map and permanent characters, which persist to disk — see Persistence). There is
no per-session isolation; the whole server is one shared table.

### DM turn pipeline (the LLM tool-calling loop)

`api/services/chat_service.py` is the most important file to understand. A chat
message flows:

1. `handle_chat` records the player event, then `plan_dm_turn`.
2. `plan_dm_turn` tries `_plan_with_llm`: it builds RAG rule context, binds
   `DM_TOOL_SCHEMAS` to the `dm`-role LLM, and asks for tool calls. If the LLM call
   throws (no key, network, etc.) it silently falls back to `_fallback_plan_tool_calls`,
   a regex-based planner that recognizes "move X to (x,y)" and inline dice.
3. Each planned `ToolCall` is dispatched by `execute_tool_call`, a big `if/elif`
   that maps tool names to `combat_service` / `map_service` / `dice_service` calls.
   `DM_AUTHORITY_TOOLS` are forced to run as `user_id="dm"` regardless of caller.
4. `narrate_dm_response` asks the LLM for a final Chinese reply grounded in the
   tool results and `current_state`; on failure it falls back to a deterministic
   summary built by `build_result_message`.

Key invariants enforced by the system prompts and normalization:
- Map coordinates are 0-based `x`/`y` everywhere; never convert/offset them.
- `current_state` JSON is the only source of truth for character facts; the DM
  must not invent class/HP/AC/etc.
- Tool args arrive in mixed camelCase/snake_case and Chinese token names; they are
  normalized via `_snake_case_arguments` and `TOKEN_ALIASES`/`_canonical_token`.
- `strip_image_payloads` removes base64 `dataUrl`s before sending state to the LLM.

When adding a DM capability: add the schema to `DM_TOOL_SCHEMAS`, a branch in
`execute_tool_call`, normalization in `_normalize_tool_call`, optionally a line in
`build_result_message`, and register authority in `DM_AUTHORITY_TOOLS` if DM-only.

### LLM configuration

`llm/registry.py` `get_llm(role)` reads `config/llm.yaml` and resolves a LangChain
chat model via `init_chat_model`. Roles: `dm`, `player`, `summarizer`, `moderator`,
plus `default` fallback. Config values like `api_key_env: DEEPSEEK_API_KEY` are
resolved against environment variables (loaded from `.env` via python-dotenv);
`${VAR}` / `$VAR` string syntax is also supported. The whole app is designed to
degrade gracefully to deterministic behavior when no key is configured.

### RAG over rules and modules

`rag/` ingests the 5e PDF and adventure-module markdown under `document/` into a
persistent Chroma collection (`dnd_rule_chunks`), embedded with
sentence-transformers. `api/services/rag_service.py` wraps this with a cached index
(`ensure_rule_index` ingests lazily on first query if the collection is empty) and,
critically, **access control**: `_rule_access_context_for_user` gives the DM full
access but restricts players via `RuleAccessContext.for_player`. Files under
`document/modules/` are auto-tagged `dm_only` (see `_is_module_document` in
`rag/rules.py`), so module secrets never reach player-facing retrieval.

### Persistence

Most state is in-memory and ephemeral. Two things persist to disk:
- The battle map, via `map_repository` (`save_default_map` / `load_default_map`).
- Permanent (reusable) characters, via `character_repository` under
  `PERMANENT_CHARACTER_DIR`, served as static `/character-assets`.

### Frontend

React 19 + Vite + TypeScript SPA in `web/src`. `api/client.ts` is the single typed
gateway to every backend endpoint (`api/types.ts` mirrors the backend shapes).
Nearly every mutating call returns the full new `GameState`, so the frontend
pattern is "send action → replace local state with the returned snapshot" rather
than optimistic local mutation. `TabletopApp.tsx` is the top-level shell;
panels (`MapView`, `CombatPanel`, `ChatPanel`, `DicePanel`, `CharacterSheet`,
`RulesLookupPage`) each map to a backend router.

## Conventions

- Backend is Python 3.10+, `from __future__ import annotations` everywhere, dataclasses
  with `frozen=True, slots=True` for value types, TypedDict for state shapes.
- Service methods return `deepcopy`-ed data so callers can't mutate internal state.
- Permission checks raise `PermissionError`; invalid input raises `ValueError`.
  Routers translate these into HTTP error responses.
- User-facing DM/UI strings are Chinese; keep code, keys, and identifiers English.
