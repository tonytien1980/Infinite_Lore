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
KNOWN_SOURCE_STATE_KEYS = {"sources", "last_scan", "failed_items"}


def _clone_default_state() -> Dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SOURCE_STATE))


def _normalize_source_list(value: Any) -> List[Dict[str, Any]]:
    return value if isinstance(value, list) else []


def _normalize_failed_items(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _normalize_failed_item_entries(value: Any, strict: bool = False) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        if strict:
            raise ValueError("failed_items must be a list")
        return []

    normalized: List[Dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, dict):
            normalized.append(dict(entry))
            continue
        if strict:
            raise ValueError("failed_items must contain objects only")
    return normalized


def _normalize_last_scan(value: Any, strict: bool = False) -> Dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    if strict:
        raise ValueError("last_scan must be an object or null")
    return None


def _normalize_text_field(value: Any, strict: bool = False, field_name: str = "field") -> str | None:
    if not isinstance(value, str):
        if strict:
            raise ValueError(f"{field_name} must be a non-empty string")
        return None

    candidate = value.strip()
    if not candidate:
        if strict:
            raise ValueError(f"{field_name} must be a non-empty string")
        return None

    return candidate


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
    if any(ch.isspace() or ord(ch) < 32 for ch in candidate):
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
    normalized_id = _normalize_text_field(normalized["id"], strict=strict, field_name="id")
    normalized_name = _normalize_text_field(normalized["name"], strict=strict, field_name="name")
    if not isinstance(normalized["source_type"], str):
        if strict:
            raise ValueError("source source_type must be a non-empty string")
        return None
    normalized_source_type = normalized["source_type"].strip()
    if not normalized_source_type:
        if strict:
            raise ValueError("source source_type must be a non-empty string")
        return None
    if normalized_source_type not in ALLOWED_SOURCE_TYPES:
        if strict:
            allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
            raise ValueError(f"source_type must be one of: {allowed}")
        return None
    normalized_url = _normalize_http_url(normalized["url"], strict=strict)
    if normalized_url is None:
        return None
    normalized["id"] = normalized_id
    normalized["name"] = normalized_name
    normalized["source_type"] = normalized_source_type
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
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, entry in enumerate(value):
        try:
            normalized_entry = _normalize_source_entry(entry, strict=strict)
        except ValueError as exc:
            if strict:
                raise ValueError(f"sources[{index}]: {exc}") from exc
            continue
        if normalized_entry is not None:
            if strict:
                source_id = normalized_entry["id"]
                source_url = normalized_entry["url"]
                if source_id in seen_ids:
                    raise ValueError(f"sources[{index}]: duplicate source id: {source_id}")
                if source_url in seen_urls:
                    raise ValueError(f"sources[{index}]: duplicate source url: {source_url}")
                seen_ids.add(source_id)
                seen_urls.add(source_url)
            normalized.append(normalized_entry)
    return normalized


def _normalize_source_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = _clone_default_state()
    if isinstance(payload, dict):
        state["sources"] = _normalize_source_entries(payload.get("sources"))
        state["last_scan"] = _normalize_last_scan(payload.get("last_scan"))
        state["failed_items"] = _normalize_failed_item_entries(payload.get("failed_items"))
        for key, value in payload.items():
            if key not in KNOWN_SOURCE_STATE_KEYS:
                state[key] = value
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


def _source_state_has_recovery_signal(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return True
    if not isinstance(payload.get("sources", []), list):
        return True
    if not isinstance(payload.get("last_scan"), (dict, type(None))):
        return True
    failed_items = payload.get("failed_items", [])
    if not isinstance(failed_items, list):
        return True
    sources = payload.get("sources", [])
    if any(_normalize_source_entry(entry) is None for entry in sources):
        return True
    if any(not isinstance(item, dict) for item in failed_items):
        return True
    return False


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
    recovered_from_corruption = False
    warning = None
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            recovered_from_corruption = True
            warning = "recovered_from_corruption"
        else:
            if _source_state_has_recovery_signal(payload):
                recovered_from_corruption = True
                warning = "recovered_from_corruption"

    state = _normalize_source_state(load_source_state(path))
    return {
        "sources": _normalize_source_entries(state.get("sources")),
        "last_scan": _normalize_last_scan(state.get("last_scan")),
        "failed_count": len(_normalize_failed_item_entries(state.get("failed_items"))),
        "failed_items": _normalize_failed_item_entries(state.get("failed_items")),
        "recovered_from_corruption": recovered_from_corruption,
        "state_warning": warning,
    }
