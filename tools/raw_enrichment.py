from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


ENRICHMENT_FILENAME = "enrichment.json"
ENRICHMENT_STATE_FILENAME = "raw-enrichment-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_enrichment_path(bundle_path: Path) -> Path:
    return bundle_path / ENRICHMENT_FILENAME


def default_enrichment_state_path(root: Path) -> Path:
    return root / "00_System" / ENRICHMENT_STATE_FILENAME


def _write_json_atomic(target_path: Path, payload: Dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target_path.parent,
        prefix=f"{target_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
        tmp_path = Path(handle.name)
    tmp_path.replace(target_path)


def _corrupt_backup_path(path: Path) -> Path:
    return path.parent / f"{path.name}.corrupt"


def _preserve_corrupt_file(path: Path) -> None:
    backup_path = _corrupt_backup_path(path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    path.replace(backup_path)


def _load_json_dict(path: Path, *, preserve_corrupt: bool = False) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        if preserve_corrupt and path.exists():
            _preserve_corrupt_file(path)
        return {}
    if not isinstance(payload, dict):
        if preserve_corrupt and path.exists():
            _preserve_corrupt_file(path)
        return {}
    return payload


def queue_bundle_for_enrichment(root: Path, bundle_path: Path) -> None:
    queued_at = now_iso()
    sidecar_path = default_enrichment_path(bundle_path)
    state_path = default_enrichment_state_path(root)
    relative_bundle_path = bundle_path.relative_to(root).as_posix()

    sidecar_payload: Dict[str, Any] = {
        "status": "pending",
        "provider": "",
        "model": "",
        "summary": "",
        "primary_domain_suggestion": "",
        "related_domain_suggestions": [],
        "topic_hints": [],
        "entity_hints": [],
        "quality_flags": [],
        "wiki_update_hints": [],
        "last_error": "",
        "queued_at": queued_at,
        "updated_at": queued_at,
    }
    existing_sidecar = _load_json_dict(sidecar_path)
    if existing_sidecar:
        sidecar_payload.update(existing_sidecar)
        sidecar_payload["status"] = "pending"
        sidecar_payload["provider"] = ""
        sidecar_payload["model"] = ""
        sidecar_payload["last_error"] = ""
        sidecar_payload.setdefault("queued_at", queued_at)
        sidecar_payload["updated_at"] = queued_at

    state_payload = _load_json_dict(state_path, preserve_corrupt=True)
    pending_bundles = state_payload.get("pending_bundles")
    if not isinstance(pending_bundles, list):
        pending_bundles = []

    filtered_pending_bundles = []
    for entry in pending_bundles:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("bundle_path") or "") == relative_bundle_path:
            continue
        filtered_pending_bundles.append(entry)

    filtered_pending_bundles.append(
        {
            "bundle_path": relative_bundle_path,
            "status": "pending",
            "provider": "",
            "model": "",
            "queued_at": queued_at,
            "updated_at": queued_at,
        }
    )
    state_payload["pending_bundles"] = filtered_pending_bundles
    state_payload.setdefault("created_at", queued_at)
    state_payload["updated_at"] = queued_at
    _write_json_atomic(state_path, state_payload)
    _write_json_atomic(sidecar_path, sidecar_payload)
