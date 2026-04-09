from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workbench.config_store import load_config, save_config
from workbench.ask_service import answer_question
from workbench.reflection_service import apply_correction, draft_correction, draft_reflection, save_reflection
from workbench.services import (
    get_dashboard,
    get_health,
    get_inbox_summary,
    get_system_info,
    import_file,
    import_url,
    list_bundles,
    list_knowledge,
)
from workbench.source_store import load_source_state, replace_sources


def create_app(vault_root: Optional[Path] = None, config_path: Optional[Path] = None) -> FastAPI:
    vault_root = (vault_root or Path.cwd()).resolve()
    config_path = config_path or Path.home() / ".config" / "infinite_lore" / "workbench.json"
    source_state_path = config_path.with_name("automation-state.json")
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

    @app.post("/api/ask/reflection/draft")
    def ask_reflection_draft(payload: dict) -> dict:
        try:
            return draft_reflection(
                vault_root=vault_root,
                ask_question=payload["question"],
                ask_mode=payload["ask_mode"],
                raw_input=payload["raw_input"],
                grounding=payload["grounding"],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/ask/reflection/confirm")
    def ask_reflection_confirm(payload: dict) -> dict:
        try:
            return save_reflection(vault_root, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/ask/correction/draft")
    def ask_correction_draft(payload: dict) -> dict:
        try:
            return draft_correction(
                vault_root=vault_root,
                ask_question=payload["question"],
                ask_mode=payload["ask_mode"],
                raw_input=payload["raw_input"],
                grounding=payload["grounding"],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/ask/correction/apply")
    def ask_correction_apply(payload: dict) -> dict:
        try:
            return apply_correction(vault_root, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/inbox/import-file")
    async def inbox_import_file(file: UploadFile = File(...), primary_domain: Optional[str] = Form(None)) -> dict:
        payload = await file.read()
        return import_file(vault_root, file.filename or "upload.bin", payload, primary_domain)

    @app.post("/api/inbox/import-url")
    def inbox_import_url(payload: dict) -> dict:
        return import_url(vault_root, payload["url"], payload.get("primary_domain"))

    @app.get("/api/inbox/sources")
    def inbox_sources() -> dict:
        return {"sources": load_source_state(source_state_path).get("sources", [])}

    @app.post("/api/inbox/sources")
    def inbox_save_sources(payload: dict) -> dict:
        sources = payload.get("sources", [])
        try:
            state = replace_sources(source_state_path, sources)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"sources": state.get("sources", [])}

    @app.get("/api/inbox/summary")
    def inbox_summary() -> dict:
        return get_inbox_summary(source_state_path)

    return app


def run() -> None:
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8765)
