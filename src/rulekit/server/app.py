"""FastAPI app factory for the designer. `rulekit serve --project P`."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import ServerState, build_router

STATIC = Path(__file__).parent / "static"


def create_app(project_root: Path) -> FastAPI:
    state = ServerState(project_root)
    app = FastAPI(title="rulekit designer", docs_url="/api/docs-ui")
    app.include_router(build_router(state))

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


def serve(project_root: Path, host: str = "127.0.0.1", port: int = 8321) -> None:
    import uvicorn

    uvicorn.run(create_app(project_root), host=host, port=port, log_level="warning")
