from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SOURCE_STATE: Dict[str, Any] = {
    "sources": [],
    "last_scan": None,
    "failed_items": [],
}


def _clone_default_state() -> Dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SOURCE_STATE))


def _normalize_source_list(value: Any) -> List[Dict[str, Any]]:
    return value if isinstance(value, list) else []


def _normalize_failed_items(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _normalize_source_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = _clone_default_state()
    if isinstance(payload, dict):
        state["sources"] = _normalize_source_list(payload.get("sources"))
        state["last_scan"] = payload.get("last_scan")
        state["failed_items"] = _normalize_failed_items(payload.get("failed_items"))
    return state


def load_source_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _clone_default_state()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return _clone_default_state()

    if not isinstance(payload, dict):
        return _clone_default_state()

    return _normalize_source_state(payload)


def save_source_state(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return payload


def replace_sources(path: Path, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = load_source_state(path)
    state["sources"] = _normalize_source_list(sources)
    return save_source_state(path, state)


def summarize_source_state(path: Path) -> Dict[str, Any]:
    state = _normalize_source_state(load_source_state(path))
    return {
        "sources": _normalize_source_list(state.get("sources")),
        "last_scan": state.get("last_scan"),
        "failed_count": len(_normalize_failed_items(state.get("failed_items"))),
        "failed_items": _normalize_failed_items(state.get("failed_items")),
    }
