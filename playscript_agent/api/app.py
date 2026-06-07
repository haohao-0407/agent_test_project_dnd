from __future__ import annotations

import argparse
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from playscript_agent.api.routers import adventures, characters, chat, combat, dice, maps, monsters, pending_actions, rag, sessions
from playscript_agent.api.services.character_repository import PERMANENT_CHARACTER_DIR
from playscript_agent.api.services.adventure_service import MODULE_ROOT


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
STATIC_ROOT = Path(__file__).resolve().parents[1] / "web" / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="DND Agent Tabletop API", version="0.1.0")
    app.include_router(sessions.router)
    app.include_router(adventures.router)
    app.include_router(characters.router)
    app.include_router(monsters.router)
    app.include_router(dice.router)
    app.include_router(maps.router)
    app.include_router(combat.router)
    app.include_router(pending_actions.router)
    app.include_router(rag.router)
    app.include_router(chat.router)
    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
    app.mount(
        "/character-assets",
        StaticFiles(directory=PERMANENT_CHARACTER_DIR, check_dir=False),
        name="character-assets",
    )
    app.mount(
        "/module-assets",
        StaticFiles(directory=MODULE_ROOT, check_dir=False),
        name="module-assets",
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_ROOT / "index.html")

    @app.get("/index.html")
    def index_html() -> FileResponse:
        return FileResponse(STATIC_ROOT / "index.html")

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DND FastAPI backend.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "playscript_agent.api.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
