from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workbench.config_store import load_config, save_config
from workbench.ask_service import answer_question
from workbench.services import get_dashboard, get_health, get_system_info, import_file, import_url, list_bundles, list_knowledge


def create_app(vault_root: Optional[Path] = None, config_path: Optional[Path] = None) -> FastAPI:
    vault_root = (vault_root or Path.cwd()).resolve()
    config_path = config_path or Path.home() / ".config" / "infinite_lore" / "workbench.json"
    static_dir = Path(__file__).resolve().parent / "static"

    app = FastAPI(title="Infinite Lore Workbench")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/dashboard")
    def dashboard() -> dict:
        return get_dashboard(vault_root)

    @app.get("/api/bundles")
    def bundles() -> list:
        return list_bundles(vault_root)

    @app.get("/api/knowledge")
    def knowledge() -> dict:
        return list_knowledge(vault_root)

    @app.get("/api/system/health")
    def system_health() -> dict:
        return get_health(vault_root)

    @app.get("/api/system/info")
    def system_info() -> dict:
        return get_system_info(vault_root)

    @app.get("/api/settings")
    def get_settings() -> dict:
        return load_config(config_path)

    @app.post("/api/settings")
    def post_settings(payload: dict) -> dict:
        return save_config(config_path, payload)

    @app.post("/api/ask")
    def ask(payload: dict) -> dict:
        settings = load_config(config_path)
        return answer_question(
            vault_root=vault_root,
            question=payload["question"],
            requested_mode=payload.get("mode", "auto"),
            settings=settings,
        )

    @app.post("/api/inbox/import-file")
    async def inbox_import_file(file: UploadFile = File(...), primary_domain: Optional[str] = Form(None)) -> dict:
        payload = await file.read()
        return import_file(vault_root, file.filename or "upload.bin", payload, primary_domain)

    @app.post("/api/inbox/import-url")
    def inbox_import_url(payload: dict) -> dict:
        return import_url(vault_root, payload["url"], payload.get("primary_domain"))

    return app


def run() -> None:
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8765)
