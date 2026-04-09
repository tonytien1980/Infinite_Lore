from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List


DEFAULT_SOURCE_STATE: Dict[str, Any] = {
    "sources": [],
    "last_scan": None,
    "failed_items": [],
}

SOURCE_REQUIRED_FIELDS = ("id", "name", "source_type", "url", "enabled")
ALLOWED_SOURCE_TYPES = {"rss-feed", "article-list-page"}


def _clone_default_state() -> Dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SOURCE_STATE))


def _normalize_source_list(value: Any) -> List[Dict[str, Any]]:
    return value if isinstance(value, list) else []


def _normalize_failed_items(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _normalize_http_url(value: Any, strict: bool = False) -> str | None:
    if not isinstance(value, str):
        if strict:
            raise ValueError("url must be a non-empty http(s) URL")
        return None

    candidate = value.strip()
    if not candidate:
        if strict:
            raise ValueError("url must be a non-empty http(s) URL")
        return None

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        if strict:
            raise ValueError("url must be a non-empty http(s) URL")
        return None

    return candidate


def _normalize_source_entry(entry: Any, strict: bool = False) -> Dict[str, Any] | None:
    if not isinstance(entry, dict):
        if strict:
            raise ValueError("each source must be an object")
        return None

    missing_fields = [field for field in SOURCE_REQUIRED_FIELDS if field not in entry]
    if missing_fields:
        if strict:
            missing = ", ".join(missing_fields)
            raise ValueError(f"source is missing required fields: {missing}")
        return None

    normalized = {field: entry[field] for field in SOURCE_REQUIRED_FIELDS}
    if not all(isinstance(normalized[field], str) for field in ("id", "name", "source_type", "url")):
        if strict:
            raise ValueError("source id, name, source_type, and url must be strings")
        return None
    if normalized["source_type"] not in ALLOWED_SOURCE_TYPES:
        if strict:
            allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
            raise ValueError(f"source_type must be one of: {allowed}")
        return None
    normalized_url = _normalize_http_url(normalized["url"], strict=strict)
    if normalized_url is None:
        return None
    normalized["url"] = normalized_url
    if not isinstance(normalized["enabled"], bool):
        if strict:
            raise ValueError("source enabled must be a boolean")
        return None
    return normalized


def _normalize_source_entries(value: Any, strict: bool = False) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        if strict:
            raise ValueError("sources must be a list")
        return []

    normalized: List[Dict[str, Any]] = []
    for index, entry in enumerate(value):
        try:
            normalized_entry = _normalize_source_entry(entry, strict=strict)
        except ValueError as exc:
            if strict:
                raise ValueError(f"sources[{index}]: {exc}") from exc
            continue
        if normalized_entry is not None:
            normalized.append(normalized_entry)
    return normalized


def _normalize_source_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = _clone_default_state()
    if isinstance(payload, dict):
        state["sources"] = _normalize_source_entries(payload.get("sources"))
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
    state = _normalize_source_state(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
        tmp_path = Path(handle.name)
    tmp_path.replace(path)
    return state


def replace_sources(path: Path, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = load_source_state(path)
    state["sources"] = _normalize_source_entries(sources, strict=True)
    return save_source_state(path, state)


def summarize_source_state(path: Path) -> Dict[str, Any]:
    state = _normalize_source_state(load_source_state(path))
    return {
        "sources": _normalize_source_entries(state.get("sources")),
        "last_scan": state.get("last_scan"),
        "failed_count": len(_normalize_failed_items(state.get("failed_items"))),
        "failed_items": _normalize_failed_items(state.get("failed_items")),
    }
