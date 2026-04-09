from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SOURCE_STATE: Dict[str, Any] = {
    "sources": [],
    "last_scan": None,
    "failed_items": [],
}


def load_source_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_SOURCE_STATE))

    payload = json.loads(path.read_text(encoding="utf-8"))
    state = json.loads(json.dumps(DEFAULT_SOURCE_STATE))
    state.update(payload)
    return state


def save_source_state(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return payload


def replace_sources(path: Path, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = load_source_state(path)
    state["sources"] = sources
    return save_source_state(path, state)


def summarize_source_state(path: Path) -> Dict[str, Any]:
    state = load_source_state(path)
    return {
        "sources": state.get("sources", []),
        "last_scan": state.get("last_scan"),
        "failed_count": len(state.get("failed_items", [])),
        "failed_items": state.get("failed_items", []),
    }
