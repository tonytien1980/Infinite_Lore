from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tools.import_bundle import import_source
from tools.source_connectors import dedup_candidates
from tools.wiki_compile import compile_bundle
from workbench.source_store import load_source_state, update_scan_state


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_local_candidates(vault_root: Path) -> List[Dict[str, Any]]:
    inbox = vault_root / "20_Raw/inbox"
    candidates: List[Dict[str, Any]] = []
    if not inbox.exists():
        return candidates
    for path in sorted(inbox.iterdir()):
        if path.is_file():
            candidates.append(
                {
                    "title": path.name,
                    "source": str(path),
                    "source_kind": "local-file",
                    "url": str(path),
                    "source_url": str(path),
                    "canonical_url": "",
                    "content_hash": "",
                    "primary_domain": "ai-application",
                }
            )
    return candidates


def run_scan(vault_root: Path, configured_sources: List[Dict[str, Any]], state_path: Path) -> Dict[str, Any]:
    state = load_source_state(state_path)
    failed_items = list(state.get("failed_items", []))
    discovered_candidates = discover_local_candidates(vault_root) + failed_items
    candidates = dedup_candidates(discovered_candidates)

    imported_count = 0
    compiled_count = 0
    new_failed: List[Dict[str, Any]] = []

    for candidate in candidates:
        try:
            bundle = import_source(vault_root, candidate["source"], candidate.get("primary_domain", "ai-application"))
            imported_count += 1
            compile_bundle(vault_root, bundle)
            compiled_count += 1
        except Exception:
            new_failed.append(candidate)

    summary = {
        "ran_at": now_iso(),
        "discovered_count": len(discovered_candidates),
        "deduplicated_count": len(candidates),
        "imported_count": imported_count,
        "compiled_count": compiled_count,
        "failed_count": len(new_failed),
    }
    update_scan_state(state_path, summary=summary, failed_items=new_failed)
    return summary
