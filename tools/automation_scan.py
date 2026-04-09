from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tools.import_bundle import import_source
from tools.source_connectors import dedup_candidates
from tools.wiki_compile import compile_bundle, read_note, write_note
from workbench.services import infer_domains
from workbench.source_store import load_source_state, summarize_source_state, update_scan_state


MAX_FAILED_RETRY_COUNT = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _local_source_key(vault_root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(vault_root)
    except ValueError:
        relative = path
    return f"local-file:{relative.as_posix()}"


def discover_local_candidates(vault_root: Path) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    inbox = vault_root / "20_Raw/inbox"
    candidates: List[Dict[str, Any]] = []
    failed_items: List[Dict[str, Any]] = []
    if not inbox.exists():
        return candidates, failed_items

    for path in sorted(inbox.iterdir()):
        if not path.is_file():
            continue
        source_key = _local_source_key(vault_root, path)
        try:
            data = path.read_bytes()
            content_text = data.decode("utf-8", errors="replace")
            primary_domain, related_domains = infer_domains(path.name, content_text)
        except Exception as exc:
            fallback_primary, fallback_related = infer_domains(path.name, "")
            failed_items.append(
                {
                    "source_key": source_key,
                    "source": str(path),
                    "source_url": str(path),
                    "url": str(path),
                    "content_hash": "",
                    "primary_domain": fallback_primary,
                    "related_domains": fallback_related,
                    "stage": "discovery-failed",
                    "error_stage": "discover",
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "retry_count": 1,
                    "last_attempt_at": now_iso(),
                    "bundle_path": "",
                }
            )
            continue
        candidate = {
            "title": path.name,
            "source_key": source_key,
            "source": str(path),
            "source_kind": "local-file",
            "url": str(path),
            "source_url": str(path),
            "canonical_url": "",
            "content_hash": _content_hash(data),
            "primary_domain": primary_domain,
            "related_domains": related_domains,
            "stage": "discovered",
            "retry_count": 0,
        }
        candidates.append(candidate)
    return candidates, failed_items


def _normalize_failed_item(item: Any) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    normalized = dict(item)
    source = normalized.get("source") or normalized.get("source_url") or normalized.get("url") or ""
    normalized["source"] = str(source)
    normalized["source_url"] = str(normalized.get("source_url") or normalized["source"])
    normalized["url"] = str(normalized.get("url") or normalized["source"])
    normalized["source_key"] = str(normalized.get("source_key") or f"retry:{normalized['source']}")
    normalized["stage"] = str(normalized.get("stage") or "import-failed")
    normalized["error_stage"] = str(normalized.get("error_stage") or "")
    normalized["retry_count"] = _retry_count(normalized)
    normalized["content_hash"] = str(normalized.get("content_hash") or "")
    normalized["primary_domain"] = str(normalized.get("primary_domain") or "ai-application")
    normalized["related_domains"] = list(normalized.get("related_domains") or [])
    return normalized


def _retry_count(item: Dict[str, Any]) -> int:
    value = item.get("retry_count", 0)
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    return count if count >= 0 else 0


def _is_retry_exhausted(item: Dict[str, Any]) -> bool:
    return _retry_count(item) >= MAX_FAILED_RETRY_COUNT


def _completed_record(candidate: Dict[str, Any], vault_root: Path, bundle_path: Path) -> Dict[str, Any]:
    return {
        "source_key": candidate["source_key"],
        "source": candidate["source"],
        "source_url": candidate["source_url"],
        "url": candidate["url"],
        "content_hash": candidate["content_hash"],
        "primary_domain": candidate["primary_domain"],
        "related_domains": list(candidate.get("related_domains", [])),
        "bundle_path": bundle_path.relative_to(vault_root).as_posix(),
        "stage": "compiled",
        "retry_count": int(candidate.get("retry_count", 0)),
        "completed_at": now_iso(),
    }


def _failure_record(
    candidate: Dict[str, Any],
    *,
    vault_root: Path,
    stage: str,
    error_stage: str,
    error: Exception,
    bundle_path: Path | None = None,
) -> Dict[str, Any]:
    record = {
        "source_key": candidate["source_key"],
        "source": candidate["source"],
        "source_url": candidate["source_url"],
        "url": candidate["url"],
        "content_hash": candidate["content_hash"],
        "primary_domain": candidate["primary_domain"],
        "related_domains": list(candidate.get("related_domains", [])),
        "stage": stage,
        "error_stage": error_stage,
        "error": f"{error.__class__.__name__}: {error}",
        "retry_count": int(candidate.get("retry_count", 0)),
        "last_attempt_at": now_iso(),
    }
    if bundle_path is not None:
        record["bundle_path"] = bundle_path.relative_to(vault_root).as_posix()
    else:
        record["bundle_path"] = str(candidate.get("bundle_path", ""))
    return record


def _processed_matches(candidate: Dict[str, Any], processed_entry: Dict[str, Any] | None) -> bool:
    if not isinstance(processed_entry, dict):
        return False
    return (
        processed_entry.get("stage") == "compiled"
        and processed_entry.get("content_hash") == candidate.get("content_hash")
        and processed_entry.get("source_key") == candidate.get("source_key")
    )


def _index_by_source_key(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for item in items:
        source_key = str(item.get("source_key") or "")
        if source_key:
            indexed[source_key] = item
    return indexed


def _unquote_scalar(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return text


def _persist_bundle_retry_count(bundle_path: Path, retry_count: int) -> None:
    metadata_path = bundle_path / "metadata.md"
    try:
        metadata, body = read_note(metadata_path)
    except Exception:
        return

    current_retry_count = _retry_count({"retry_count": metadata.get("compile_retry_count", 0)})
    if retry_count <= current_retry_count:
        return

    metadata["compile_retry_count"] = retry_count
    metadata["updated_at"] = now_iso()
    write_note(metadata_path, metadata, body)


def _recover_processed_sources_from_bundles(vault_root: Path) -> Dict[str, Dict[str, Any]]:
    inbox = vault_root / "20_Raw/inbox"
    recovered: Dict[str, Dict[str, Any]] = {}
    if not inbox.exists():
        return recovered

    for bundle_path in sorted(path for path in inbox.iterdir() if path.is_dir()):
        metadata_path = bundle_path / "metadata.md"
        if not metadata_path.exists():
            continue

        try:
            metadata, _ = read_note(metadata_path)
        except Exception:
            continue

        source_ref = _unquote_scalar(str(metadata.get("source_ref") or ""))
        content_hash = str(metadata.get("content_hash") or "")
        if not source_ref or not content_hash:
            continue

        source_path = Path(source_ref)
        if not source_path.is_absolute():
            source_path = vault_root / source_path

        try:
            source_path.relative_to(vault_root)
        except ValueError:
            continue

        source_key = _local_source_key(vault_root, source_path)
        compiled_at = str(metadata.get("compiled_at") or "").strip()
        compiled_note_refs = metadata.get("compiled_note_refs")
        has_compiled_proof = bool(compiled_at or compiled_note_refs)
        compile_retry_count = _retry_count({"retry_count": metadata.get("compile_retry_count", 0)})
        recovered[source_key] = {
            "source_key": source_key,
            "source": str(source_path),
            "source_url": str(source_path),
            "url": str(source_path),
            "content_hash": content_hash,
            "primary_domain": str(metadata.get("primary_domain") or "ai-application"),
            "related_domains": list(metadata.get("related_domains") or []),
            "bundle_path": bundle_path.relative_to(vault_root).as_posix(),
            "stage": "compiled" if has_compiled_proof else "imported",
            "retry_count": 0 if has_compiled_proof else compile_retry_count,
            "completed_at": compiled_at if has_compiled_proof else str(metadata.get("imported_at") or ""),
        }

    return recovered


def run_scan(vault_root: Path, configured_sources: List[Dict[str, Any]], state_path: Path) -> Dict[str, Any]:
    state = load_source_state(state_path)
    state_summary = summarize_source_state(state_path)
    processed_sources = state.get("processed_sources", {})
    if state_summary.get("recovered_from_corruption"):
        recovered_processed_sources = _recover_processed_sources_from_bundles(vault_root)
        if recovered_processed_sources:
            merged_processed_sources = dict(processed_sources) if isinstance(processed_sources, dict) else {}
            merged_processed_sources.update(recovered_processed_sources)
            processed_sources = merged_processed_sources
    exhausted_failed_items = [_normalize_failed_item(item) for item in state.get("exhausted_failed_items", [])]
    exhausted_failed_items = [item for item in exhausted_failed_items if item is not None]
    failed_items = [_normalize_failed_item(item) for item in state.get("failed_items", [])]
    failed_items = [item for item in failed_items if item is not None]
    retryable_failed_items = [item for item in failed_items if not _is_retry_exhausted(item)]

    processed_by_key = _index_by_source_key(list(processed_sources.values())) if isinstance(processed_sources, dict) else {}
    retryable_by_key = _index_by_source_key(retryable_failed_items)
    exhausted_by_key = _index_by_source_key(exhausted_failed_items)
    resolved_source_keys: set[str] = set()

    discovered_candidates, discovery_failed_items = discover_local_candidates(vault_root)
    fresh_candidates: List[Dict[str, Any]] = []
    skipped_count = 0
    blocked_exhausted_count = 0
    for candidate in discovered_candidates:
        source_key = candidate["source_key"]
        content_hash = candidate["content_hash"]
        processed_entry = processed_by_key.get(source_key)
        if _processed_matches(candidate, processed_entry):
            skipped_count += 1
            resolved_source_keys.add(source_key)
            continue
        if (
            isinstance(processed_entry, dict)
            and processed_entry.get("stage") == "imported"
            and processed_entry.get("content_hash") == content_hash
            and processed_entry.get("bundle_path")
        ):
            merged_candidate = dict(candidate)
            merged_candidate["stage"] = "imported"
            merged_candidate["bundle_path"] = str(processed_entry.get("bundle_path") or "")
            merged_candidate["retry_count"] = int(processed_entry.get("retry_count", 0))
            if not merged_candidate.get("primary_domain"):
                merged_candidate["primary_domain"] = str(processed_entry.get("primary_domain") or "")
            if not merged_candidate.get("related_domains"):
                merged_candidate["related_domains"] = list(processed_entry.get("related_domains") or [])
            fresh_candidates.append(merged_candidate)
            continue
        exhausted_entry = exhausted_by_key.get(source_key)
        if exhausted_entry and exhausted_entry.get("content_hash") and exhausted_entry.get("content_hash") == content_hash:
            blocked_exhausted_count += 1
            continue
        retry_entry = retryable_by_key.get(source_key)
        if retry_entry and (not retry_entry.get("content_hash") or retry_entry.get("content_hash") == content_hash):
            merged_candidate = dict(candidate)
            merged_candidate["stage"] = str(retry_entry.get("stage") or "import-failed")
            merged_candidate["retry_count"] = _retry_count(retry_entry)
            merged_candidate["bundle_path"] = str(retry_entry.get("bundle_path") or "")
            if not merged_candidate.get("primary_domain"):
                merged_candidate["primary_domain"] = str(retry_entry.get("primary_domain") or "")
            if not merged_candidate.get("related_domains"):
                merged_candidate["related_domains"] = list(retry_entry.get("related_domains") or [])
            fresh_candidates.append(merged_candidate)
            continue
        fresh_candidates.append(candidate)

    candidates = dedup_candidates(fresh_candidates)

    imported_count = 0
    compiled_count = 0
    new_failed: List[Dict[str, Any]] = []
    added_exhausted_items: List[Dict[str, Any]] = []
    new_processed_sources = dict(processed_sources) if isinstance(processed_sources, dict) else {}
    updated_retry_keys: set[str] = set()

    for discovery_failure in discovery_failed_items:
        source_key = str(discovery_failure.get("source_key") or "")
        if not source_key:
            continue

        exhausted_entry = exhausted_by_key.get(source_key)
        if exhausted_entry:
            continue

        retry_entry = retryable_by_key.get(source_key)
        retry_count = _retry_count(retry_entry) + 1 if retry_entry else int(discovery_failure.get("retry_count", 1))
        failure = dict(discovery_failure)
        failure["retry_count"] = retry_count
        failure["retry_status"] = "exhausted" if retry_count >= MAX_FAILED_RETRY_COUNT else "retrying"
        if retry_count >= MAX_FAILED_RETRY_COUNT:
            added_exhausted_items.append(failure)
        else:
            new_failed.append(failure)
        updated_retry_keys.add(source_key)

    for candidate in candidates:
        retry_count = int(candidate.get("retry_count", 0))
        if candidate.get("stage") == "compiled":
            continue

        if candidate.get("stage") == "imported" and candidate.get("bundle_path"):
            bundle_path = vault_root / candidate["bundle_path"]
            try:
                compile_bundle(vault_root, bundle_path)
            except Exception as exc:
                _persist_bundle_retry_count(bundle_path, retry_count + 1)
                failure = _failure_record(
                    candidate,
                    vault_root=vault_root,
                    stage="imported",
                    error_stage="compile",
                    error=exc,
                    bundle_path=bundle_path,
                )
                failure["retry_count"] = retry_count + 1
                if _retry_count(failure) >= MAX_FAILED_RETRY_COUNT:
                    failure["retry_status"] = "exhausted"
                    added_exhausted_items.append(failure)
                else:
                    failure["retry_status"] = "retrying"
                    new_failed.append(failure)
                updated_retry_keys.add(str(candidate.get("source_key", "")))
                continue

            compiled_count += 1
            new_processed_sources[candidate["source_key"]] = _completed_record(candidate, vault_root, bundle_path)
            resolved_source_keys.add(candidate["source_key"])
            continue

        try:
            bundle = import_source(
                vault_root,
                candidate["source"],
                candidate.get("primary_domain", "ai-application"),
                candidate.get("related_domains", []),
            )
            imported_count += 1
        except Exception as exc:
            failure = _failure_record(
                candidate,
                vault_root=vault_root,
                stage="import-failed",
                error_stage="import",
                error=exc,
            )
            failure["retry_count"] = retry_count + 1
            if _retry_count(failure) >= MAX_FAILED_RETRY_COUNT:
                failure["retry_status"] = "exhausted"
                added_exhausted_items.append(failure)
            else:
                failure["retry_status"] = "retrying"
                new_failed.append(failure)
            updated_retry_keys.add(str(candidate.get("source_key", "")))
            continue

        try:
            compile_bundle(vault_root, bundle)
        except Exception as exc:
            _persist_bundle_retry_count(bundle, retry_count + 1)
            failure = _failure_record(
                candidate,
                vault_root=vault_root,
                stage="imported",
                error_stage="compile",
                error=exc,
                bundle_path=bundle,
            )
            failure["retry_count"] = retry_count + 1
            if _retry_count(failure) >= MAX_FAILED_RETRY_COUNT:
                failure["retry_status"] = "exhausted"
                added_exhausted_items.append(failure)
            else:
                failure["retry_status"] = "retrying"
                new_failed.append(failure)
            updated_retry_keys.add(str(candidate.get("source_key", "")))
            continue

        compiled_count += 1
        new_processed_sources[candidate["source_key"]] = _completed_record(candidate, vault_root, bundle)
        resolved_source_keys.add(candidate["source_key"])

    carry_failed_items = [
        item
        for item in retryable_failed_items
        if item.get("source_key") not in resolved_source_keys and item.get("source_key") not in updated_retry_keys
    ]
    carry_exhausted_items = [
        item
        for item in exhausted_failed_items
        if item.get("source_key") not in resolved_source_keys and item.get("source_key") not in updated_retry_keys
    ]
    new_failed = carry_failed_items + new_failed

    summary = {
        "ran_at": now_iso(),
        "discovered_count": len(discovered_candidates) + len(discovery_failed_items),
        "skipped_count": skipped_count,
        "blocked_exhausted_count": blocked_exhausted_count,
        "deduplicated_count": len(candidates),
        "imported_count": imported_count,
        "compiled_count": compiled_count,
        "failed_count": len(new_failed),
        "exhausted_failed_count": len(carry_exhausted_items) + len(added_exhausted_items),
        "retry_limit": MAX_FAILED_RETRY_COUNT,
    }
    update_scan_state(
        state_path,
        summary=summary,
        failed_items=new_failed,
        exhausted_failed_items=carry_exhausted_items + added_exhausted_items,
        processed_sources=new_processed_sources,
    )
    return summary
