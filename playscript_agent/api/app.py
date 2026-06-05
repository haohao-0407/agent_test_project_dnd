from __future__ import annotations

import argparse
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from playscript_agent.api.routers import characters, chat, dice, maps, rag, sessions


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
STATIC_ROOT = Path(__file__).resolve().parents[1] / "web" / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="DND Agent Tabletop API", version="0.1.0")
    app.include_router(sessions.router)
    app.include_router(characters.router)
    app.include_router(dice.router)
    app.include_router(maps.router)
    app.include_router(rag.router)
    app.include_router(chat.router)
    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

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
