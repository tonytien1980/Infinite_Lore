from __future__ import annotations

import json
import hashlib
import tempfile
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

from tools.import_bundle import import_source
from tools.source_connectors import choose_canonical_url, dedup_candidates, discover_article_list_items, discover_rss_items
from tools.wiki_compile import compile_bundle, read_note, write_note
from workbench.services import infer_domains
from workbench.source_store import load_source_state, summarize_source_state, update_scan_state


MAX_FAILED_RETRY_COUNT = 2
CONFIGURED_ARTICLE_RETRY_COOLDOWN = timedelta(hours=1)
BUNDLE_RETRY_STATE_FILENAME = ".automation-retry.json"


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


def _configured_source_key(source: Dict[str, Any]) -> str:
    source_id = str(source.get("id") or "").strip()
    if not source_id:
        source_url = str(source.get("url") or "").strip()
        source_id = _content_hash(source_url.encode("utf-8"))[:12] if source_url else "unknown"
    return f"configured-source:{source_id}"


def _configured_article_key(article_url: str) -> str:
    return f"configured-article:{choose_canonical_url(article_url)}"


def _active_configured_source_urls(configured_sources: List[Dict[str, Any]]) -> set[str]:
    urls: set[str] = set()
    for source in configured_sources:
        if not isinstance(source, dict):
            continue
        if source.get("enabled") is False:
            continue
        if str(source.get("source_type") or "") not in {"rss-feed", "article-list-page"}:
            continue
        source_url = str(source.get("url") or "").strip()
        if source_url:
            urls.add(source_url)
    return urls


def _parse_utc_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _configured_article_retry_ready(item: Dict[str, Any], current_time: datetime) -> bool:
    source_key = str(item.get("source_key") or "")
    if not source_key.startswith("configured-article:"):
        return False
    last_attempt = _parse_utc_timestamp(str(item.get("last_attempt_at") or item.get("completed_at") or ""))
    if last_attempt is None:
        return False
    return current_time - last_attempt >= CONFIGURED_ARTICLE_RETRY_COOLDOWN


def _is_stale_configured_state_item(
    item: Dict[str, Any],
    active_source_urls: set[str],
    successful_source_urls: set[str],
    discovered_configured_article_keys: set[str],
) -> bool:
    source_key = str(item.get("source_key") or "")
    if not source_key.startswith("configured-"):
        return False
    source_url = str(item.get("source_url") or "").strip()
    if source_url not in active_source_urls:
        return True
    if source_url not in successful_source_urls:
        return False
    if source_key.startswith("configured-article:"):
        return source_key not in discovered_configured_article_keys
    return True


def _fetch_url_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def _configured_source_failure(
    source: Dict[str, Any],
    *,
    error_stage: str,
    error: Exception,
    content_hash: str = "",
) -> Dict[str, Any]:
    source_url = str(source.get("url") or "")
    fallback_primary, fallback_related = infer_domains(str(source.get("name") or source_url), source_url)
    return {
        "source_key": _configured_source_key(source),
        "source": source_url,
        "source_url": source_url,
        "url": source_url,
        "content_hash": content_hash,
        "primary_domain": fallback_primary,
        "related_domains": fallback_related,
        "stage": "discovery-failed",
        "error_stage": error_stage,
        "error": f"{error.__class__.__name__}: {error}",
        "retry_count": 1,
        "last_attempt_at": now_iso(),
        "bundle_path": "",
    }


def discover_configured_candidates(
    configured_sources: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], set[str], set[str]]:
    candidates: List[Dict[str, Any]] = []
    failed_items: List[Dict[str, Any]] = []
    successful_source_keys: set[str] = set()
    successful_source_urls: set[str] = set()

    for source in configured_sources:
        if not isinstance(source, dict):
            continue
        if source.get("enabled") is False:
            continue

        source_type = str(source.get("source_type") or "")
        source_url = str(source.get("url") or "").strip()
        if not source_url or source_type not in {"rss-feed", "article-list-page"}:
            continue

        try:
            source_bytes = _fetch_url_bytes(source_url)
        except Exception as exc:
            failed_items.append(_configured_source_failure(source, error_stage="fetch", error=exc))
            continue

        try:
            if source_type == "rss-feed":
                discovered_items = discover_rss_items(source_bytes, source_url)
            else:
                discovered_items = discover_article_list_items(source_bytes.decode("utf-8", errors="replace"), source_url)
        except Exception as exc:
            failed_items.append(
                _configured_source_failure(
                    source,
                    error_stage="discover",
                    error=exc,
                    content_hash=_content_hash(source_bytes),
                )
            )
            continue

        successful_source_keys.add(_configured_source_key(source))
        successful_source_urls.add(source_url)
        for item in discovered_items:
            article_url = str(item.get("url") or "").strip()
            if not article_url:
                continue
            canonical_url = choose_canonical_url(article_url)
            source_key = _configured_article_key(article_url)
            primary_domain, related_domains = infer_domains(str(item.get("title") or article_url), article_url)
            candidates.append(
                {
                    "title": str(item.get("title") or article_url),
                    "source_key": source_key,
                    "source": article_url,
                    "source_kind": "configured-source",
                    "source_type": source_type,
                    "url": article_url,
                    "source_url": source_url,
                    "canonical_url": canonical_url,
                    "content_hash": _content_hash(canonical_url.encode("utf-8")),
                    "primary_domain": primary_domain,
                    "related_domains": related_domains,
                    "stage": "discovered",
                    "retry_count": 0,
                }
            )

    return candidates, failed_items, successful_source_keys, successful_source_urls


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
    source_key = str(candidate.get("source_key") or "")
    if source_key.startswith("configured-article:"):
        return processed_entry.get("stage") == "compiled" and processed_entry.get("source_key") == source_key
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


def _bundle_retry_state_path(bundle_path: Path) -> Path:
    return bundle_path / BUNDLE_RETRY_STATE_FILENAME


def _load_bundle_retry_count(bundle_path: Path, metadata_retry_count: Any = 0) -> int:
    metadata_count = _retry_count({"retry_count": metadata_retry_count})
    sidecar_path = _bundle_retry_state_path(bundle_path)
    if sidecar_path.exists():
        try:
            sidecar_payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
        else:
            if isinstance(sidecar_payload, dict):
                sidecar_count = _retry_count({"retry_count": sidecar_payload.get("compile_retry_count", 0)})
                return max(sidecar_count, metadata_count)

    return metadata_count


def _write_bundle_retry_sidecar(bundle_path: Path, retry_count: int) -> None:
    sidecar_path = _bundle_retry_state_path(bundle_path)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "compile_retry_count": retry_count,
        "updated_at": now_iso(),
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=bundle_path,
        prefix=f"{sidecar_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
        tmp_path = Path(handle.name)
    tmp_path.replace(sidecar_path)


def _persist_bundle_retry_count(bundle_path: Path, retry_count: int) -> None:
    try:
        current_retry_count = _load_bundle_retry_count(bundle_path)
    except Exception:
        return

    if retry_count <= current_retry_count:
        return

    try:
        _write_bundle_retry_sidecar(bundle_path, retry_count)
    except Exception:
        pass

    metadata_path = bundle_path / "metadata.md"
    try:
        metadata, body = read_note(metadata_path)
    except Exception:
        return

    metadata["compile_retry_count"] = retry_count
    metadata["updated_at"] = now_iso()
    try:
        write_note(metadata_path, metadata, body)
    except Exception:
        return


def _resolve_source_path(vault_root: Path, source: str) -> Path:
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = vault_root / source_path
    return source_path


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
        compile_retry_count = _load_bundle_retry_count(bundle_path, metadata.get("compile_retry_count", 0))
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
    active_configured_source_urls = _active_configured_source_urls(configured_sources)
    current_time = _parse_utc_timestamp(now_iso()) or datetime.now(timezone.utc)
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

    (
        configured_candidates,
        configured_failed_items,
        configured_successful_source_keys,
        configured_successful_source_urls,
    ) = discover_configured_candidates(configured_sources)
    discovered_candidates, discovery_failed_items = discover_local_candidates(vault_root)
    discovered_configured_article_keys = {
        candidate["source_key"] for candidate in configured_candidates if str(candidate.get("source_key") or "").startswith("configured-article:")
    }

    exhausted_failed_items = [
        item
        for item in exhausted_failed_items
        if not _is_stale_configured_state_item(
            item,
            active_configured_source_urls,
            configured_successful_source_urls,
            discovered_configured_article_keys,
        )
    ]
    failed_items = [
        item
        for item in failed_items
        if not _is_stale_configured_state_item(
            item,
            active_configured_source_urls,
            configured_successful_source_urls,
            discovered_configured_article_keys,
        )
    ]
    retryable_failed_items = [item for item in failed_items if not _is_retry_exhausted(item)]

    processed_by_key = _index_by_source_key(list(processed_sources.values())) if isinstance(processed_sources, dict) else {}
    retryable_by_key = _index_by_source_key(retryable_failed_items)
    exhausted_by_key = _index_by_source_key(exhausted_failed_items)
    resolved_source_keys: set[str] = set()
    fresh_candidates: List[Dict[str, Any]] = []
    skipped_count = 0
    blocked_exhausted_count = 0
    updated_retry_keys: set[str] = set(configured_successful_source_keys)

    for candidate in configured_candidates + discovered_candidates:
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
            if _is_retry_exhausted(processed_entry):
                blocked_exhausted_count += 1
                continue
            retry_entry = retryable_by_key.get(source_key)
            merged_candidate = dict(candidate)
            merged_candidate["stage"] = "imported"
            merged_candidate["bundle_path"] = str(processed_entry.get("bundle_path") or "")
            merged_candidate["retry_count"] = max(_retry_count(processed_entry), _retry_count(retry_entry) if retry_entry else 0)
            if not merged_candidate.get("primary_domain"):
                merged_candidate["primary_domain"] = str(processed_entry.get("primary_domain") or "")
            if not merged_candidate.get("related_domains"):
                merged_candidate["related_domains"] = list(processed_entry.get("related_domains") or [])
            fresh_candidates.append(merged_candidate)
            continue
        exhausted_entry = exhausted_by_key.get(source_key)
        if exhausted_entry:
            if source_key.startswith("configured-article:"):
                if not _configured_article_retry_ready(exhausted_entry, current_time):
                    blocked_exhausted_count += 1
                    continue
                merged_candidate = dict(candidate)
                if str(exhausted_entry.get("stage") or "") == "imported" and exhausted_entry.get("bundle_path"):
                    merged_candidate["stage"] = "imported"
                    merged_candidate["bundle_path"] = str(exhausted_entry.get("bundle_path") or "")
                merged_candidate["retry_count"] = max(
                    _retry_count(exhausted_entry),
                    _retry_count(retryable_by_key.get(source_key)) if retryable_by_key.get(source_key) else 0,
                )
                if not merged_candidate.get("primary_domain"):
                    merged_candidate["primary_domain"] = str(exhausted_entry.get("primary_domain") or "")
                if not merged_candidate.get("related_domains"):
                    merged_candidate["related_domains"] = list(exhausted_entry.get("related_domains") or [])
                fresh_candidates.append(merged_candidate)
                continue
            if exhausted_entry.get("content_hash") and exhausted_entry.get("content_hash") == content_hash:
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

    discovered_source_keys = {candidate["source_key"] for candidate in configured_candidates + discovered_candidates}
    for retry_entry in retryable_failed_items:
        source_key = str(retry_entry.get("source_key") or "")
        if not source_key or source_key in discovered_source_keys:
            continue
        if str(retry_entry.get("stage") or "") == "imported":
            bundle_path = str(retry_entry.get("bundle_path") or "")
            if not bundle_path:
                continue

            source_path = _resolve_source_path(vault_root, str(retry_entry.get("source") or ""))
            if source_path.exists():
                continue

            retry_bundle_path = vault_root / bundle_path
            if not retry_bundle_path.exists():
                continue

            merged_candidate = dict(retry_entry)
            merged_candidate["stage"] = "imported"
            merged_candidate["bundle_path"] = bundle_path
            merged_candidate["retry_count"] = _retry_count(retry_entry)
            if not merged_candidate.get("primary_domain"):
                merged_candidate["primary_domain"] = str(retry_entry.get("primary_domain") or "")
            if not merged_candidate.get("related_domains"):
                merged_candidate["related_domains"] = list(retry_entry.get("related_domains") or [])
            fresh_candidates.append(merged_candidate)

    if state_summary.get("recovered_from_corruption"):
        fresh_source_keys = {candidate["source_key"] for candidate in fresh_candidates}
        for processed_entry in processed_by_key.values():
            if not isinstance(processed_entry, dict):
                continue
            if processed_entry.get("stage") != "imported" or not processed_entry.get("bundle_path"):
                continue

            source_key = str(processed_entry.get("source_key") or "")
            if not source_key or source_key in discovered_source_keys or source_key in fresh_source_keys:
                continue

            source_path = _resolve_source_path(vault_root, str(processed_entry.get("source") or ""))
            if source_path.exists():
                continue

            bundle_path = vault_root / str(processed_entry.get("bundle_path") or "")
            if not bundle_path.exists():
                continue

            if _is_retry_exhausted(processed_entry):
                blocked_exhausted_count += 1
                continue

            retry_entry = retryable_by_key.get(source_key)
            merged_candidate = dict(processed_entry)
            merged_candidate["stage"] = "imported"
            merged_candidate["retry_count"] = max(_retry_count(processed_entry), _retry_count(retry_entry) if retry_entry else 0)
            if not merged_candidate.get("primary_domain"):
                merged_candidate["primary_domain"] = str(processed_entry.get("primary_domain") or "")
            if not merged_candidate.get("related_domains"):
                merged_candidate["related_domains"] = list(processed_entry.get("related_domains") or [])
            fresh_candidates.append(merged_candidate)

    candidates = dedup_candidates(fresh_candidates)

    imported_count = 0
    compiled_count = 0
    new_failed: List[Dict[str, Any]] = []
    added_exhausted_items: List[Dict[str, Any]] = []
    new_processed_sources = dict(processed_sources) if isinstance(processed_sources, dict) else {}

    for discovery_failure in configured_failed_items + discovery_failed_items:
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
        "discovered_count": len(configured_candidates) + len(configured_failed_items) + len(discovered_candidates) + len(discovery_failed_items),
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
