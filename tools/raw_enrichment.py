from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

from workbench.config_store import load_config
from workbench.provider_router import resolve_route_provider


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


def _list_of_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _base_sidecar_payload(queued_at: str) -> Dict[str, Any]:
    return {
        "status": "pending",
        "provider": "",
        "model": "",
        "summary": "",
        "primary_domain_suggestion": "",
        "related_domains_suggestion": [],
        "topic_tags": [],
        "entity_hints": [],
        "quality_flags": [],
        "wiki_update_hint": "",
        "failure_reason": "",
        "queued_at": queued_at,
        "started_at": "",
        "completed_at": "",
        "updated_at": queued_at,
        "last_error": "",
    }


def _load_sidecar(bundle_path: Path, queued_at: Optional[str] = None) -> Dict[str, Any]:
    timestamp = queued_at or now_iso()
    sidecar = _base_sidecar_payload(timestamp)
    existing = _load_json_dict(default_enrichment_path(bundle_path))
    if existing:
        sidecar.update(existing)
        sidecar.setdefault("queued_at", timestamp)
    return sidecar


def _normalize_pending_entry(bundle_path: str, queued_at: str) -> Dict[str, Any]:
    return {
        "bundle_path": bundle_path,
        "status": "pending",
        "provider": "",
        "model": "",
        "failure_reason": "",
        "queued_at": queued_at,
        "updated_at": queued_at,
    }


def _resolve_bundle_path_text(root: Path, bundle_path_text: str, *, require_existing_dir: bool) -> tuple[Path, str]:
    root_resolved = root.resolve()
    bundle_path_text = bundle_path_text.strip()
    if not bundle_path_text:
        raise ValueError("Bundle path is required")

    bundle_path, relative_bundle_path = _canonicalize_bundle_path(root, root / bundle_path_text)
    resolved_bundle_path = bundle_path.resolve()
    if require_existing_dir and not resolved_bundle_path.is_dir():
        raise ValueError(f"Bundle path does not exist as a directory: {relative_bundle_path}")

    return bundle_path, relative_bundle_path


def _canonicalize_bundle_path(root: Path, bundle_path: Path) -> tuple[Path, str]:
    root_resolved = root.resolve()
    resolved_bundle_path = bundle_path.resolve()
    try:
        relative_bundle_path = resolved_bundle_path.relative_to(root_resolved).as_posix()
    except ValueError as exc:
        raise ValueError("Bundle path must be inside the vault") from exc

    if Path(relative_bundle_path).parts[:1] != ("20_Raw",):
        raise ValueError("Bundle path must point to a raw bundle under 20_Raw")

    return root / relative_bundle_path, relative_bundle_path


def queue_bundle_for_enrichment(root: Path, bundle_path: Path) -> None:
    bundle_path, relative_bundle_path = _canonicalize_bundle_path(root, bundle_path)
    queued_at = now_iso()
    sidecar_path = default_enrichment_path(bundle_path)
    state_path = default_enrichment_state_path(root)

    sidecar_payload = _load_sidecar(bundle_path, queued_at)
    sidecar_payload.update(
        {
            "status": "pending",
            "provider": "",
            "model": "",
            "failure_reason": "",
            "started_at": "",
            "completed_at": "",
            "updated_at": queued_at,
            "last_error": "",
        }
    )

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

    filtered_pending_bundles.append(_normalize_pending_entry(relative_bundle_path, queued_at))
    state_payload["pending_bundles"] = filtered_pending_bundles
    state_payload.setdefault("created_at", queued_at)
    state_payload["updated_at"] = queued_at
    _write_json_atomic(state_path, state_payload)
    _write_json_atomic(sidecar_path, sidecar_payload)


def retry_bundle_for_enrichment(root: Path, bundle_path_text: str) -> Dict[str, str]:
    bundle_path, relative_bundle_path = _resolve_bundle_path_text(root, bundle_path_text, require_existing_dir=True)
    queue_bundle_for_enrichment(root, bundle_path)
    sidecar = _load_sidecar(bundle_path)
    return {
        "bundle_path": relative_bundle_path,
        "enrichment_status": str(sidecar.get("status") or ""),
        "enrichment_updated_at": str(sidecar.get("updated_at") or ""),
    }


def dismiss_bundle_from_enrichment_queue(root: Path, bundle_path_text: str) -> Dict[str, Any]:
    _, relative_bundle_path = _resolve_bundle_path_text(root, bundle_path_text, require_existing_dir=False)
    state_path = default_enrichment_state_path(root)
    state_payload = _load_json_dict(state_path, preserve_corrupt=True)
    pending_bundles = state_payload.get("pending_bundles")
    if not isinstance(pending_bundles, list):
        pending_bundles = []

    retained_entries = []
    removed = 0
    for entry in pending_bundles:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("bundle_path") or "") == relative_bundle_path:
            removed += 1
            continue
        retained_entries.append(entry)

    if removed == 0:
        raise ValueError(f"No active queue entry exists for bundle: {relative_bundle_path}")

    timestamp = now_iso()
    state_payload["pending_bundles"] = retained_entries
    state_payload.setdefault("created_at", timestamp)
    state_payload["updated_at"] = timestamp
    _write_json_atomic(state_path, state_payload)

    return {"bundle_path": relative_bundle_path, "dismissed": True}


def _default_generate_enrichment(
    *,
    bundle_path: Path,
    route: Dict[str, str],
    metadata_text: str,
    content_text: str,
) -> Dict[str, Any]:
    client_kwargs: Dict[str, Any] = {"api_key": route["api_key"]}
    if route.get("base_url"):
        client_kwargs["base_url"] = route["base_url"]

    prompt = (
        "You are enriching raw knowledge captures for a personal LLM wiki. "
        "Return JSON only with these keys: primary_domain_suggestion, related_domains_suggestion, "
        "summary, topic_tags, entity_hints, quality_flags, wiki_update_hint.\n\n"
        f"Bundle path: {bundle_path.name}\n\n"
        f"Metadata:\n{metadata_text[:4000]}\n\n"
        f"Content:\n{content_text[:12000]}"
    )
    client = OpenAI(**client_kwargs)
    response = client.responses.create(model=route["model"], input=prompt)
    output_text = response.output_text.strip()
    payload = json.loads(output_text)
    if not isinstance(payload, dict):
        raise ValueError("OpenAI enrichment output was not a JSON object")
    return payload


def _normalize_generated_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    related_domains = payload.get("related_domains_suggestion")
    if related_domains is None:
        related_domains = payload.get("related_domain_suggestions")

    topic_tags = payload.get("topic_tags")
    if topic_tags is None:
        topic_tags = payload.get("topic_hints")

    wiki_update_hint = payload.get("wiki_update_hint")
    if wiki_update_hint is None:
        wiki_update_hints = payload.get("wiki_update_hints")
        if isinstance(wiki_update_hints, list) and wiki_update_hints:
            wiki_update_hint = str(wiki_update_hints[0])
        else:
            wiki_update_hint = ""

    return {
        "summary": str(payload.get("summary") or ""),
        "primary_domain_suggestion": str(payload.get("primary_domain_suggestion") or ""),
        "related_domains_suggestion": _list_of_strings(related_domains),
        "topic_tags": _list_of_strings(topic_tags),
        "entity_hints": _list_of_strings(payload.get("entity_hints")),
        "quality_flags": _list_of_strings(payload.get("quality_flags")),
        "wiki_update_hint": str(wiki_update_hint or ""),
    }


def _write_sidecar_result(
    bundle_path: Path,
    *,
    status: str,
    provider: str,
    model: str,
    failure_reason: str,
    started_at: str = "",
    completed_at: str = "",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sidecar = _load_sidecar(bundle_path)
    sidecar.update(
        {
            "status": status,
            "provider": provider,
            "model": model,
            "failure_reason": failure_reason,
            "started_at": started_at,
            "completed_at": completed_at,
            "updated_at": now_iso(),
            "last_error": failure_reason,
        }
    )
    if payload:
        sidecar.update(payload)
    if not failure_reason:
        sidecar["last_error"] = ""
    _write_json_atomic(default_enrichment_path(bundle_path), sidecar)
    return sidecar


def _build_result(
    root: Path,
    bundle_path: Path,
    *,
    status: str,
    reason: str,
    provider: str,
    model: str,
) -> Dict[str, Any]:
    return {
        "bundle_path": bundle_path.relative_to(root).as_posix(),
        "status": status,
        "reason": reason,
        "provider": provider,
        "model": model,
        "failure_reason": reason,
    }


def _record_failed_bundle(
    root: Path,
    bundle_path: Path,
    *,
    provider: str,
    model: str,
    reason: str,
    started_at: str = "",
    write_sidecar: bool = True,
) -> Dict[str, Any]:
    if write_sidecar:
        _write_sidecar_result(
            bundle_path,
            status="failed",
            provider=provider,
            model=model,
            failure_reason=reason,
            started_at=started_at,
        )
    return _build_result(root, bundle_path, status="failed", reason=reason, provider=provider, model=model)


def enrich_bundle(
    root: Path,
    bundle_path: Path,
    settings: Dict[str, Any],
    *,
    generate_enrichment: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    route = resolve_route_provider(settings, "enrich_raw")
    if not bundle_path.exists():
        return _record_failed_bundle(
            root,
            bundle_path,
            provider="",
            model="",
            reason=f"Queued bundle path is missing: {bundle_path.relative_to(root).as_posix()}",
            write_sidecar=False,
        )

    if not route:
        reason = "No runnable provider is configured for enrich_raw."
        _write_sidecar_result(bundle_path, status="deferred", provider="", model="", failure_reason=reason)
        return _build_result(root, bundle_path, status="deferred", reason="no_runnable_provider", provider="", model="")

    provider = route["provider"]
    model = route["model"]
    if provider != "openai":
        reason = f"Provider '{provider}' is not supported by the minimal raw enrichment runner yet."
        _write_sidecar_result(bundle_path, status="deferred", provider=provider, model=model, failure_reason=reason)
        return _build_result(root, bundle_path, status="deferred", reason="unsupported_provider", provider=provider, model=model)

    metadata_path = bundle_path / "metadata.md"
    content_path = bundle_path / "content.md"
    started_at = now_iso()
    try:
        metadata_text = metadata_path.read_text(encoding="utf-8") if metadata_path.exists() else ""
        content_text = content_path.read_text(encoding="utf-8") if content_path.exists() else ""
    except (OSError, UnicodeDecodeError) as exc:
        return _record_failed_bundle(
            root,
            bundle_path,
            provider=provider,
            model=model,
            reason=str(exc) or exc.__class__.__name__,
            started_at=started_at,
        )

    generator = generate_enrichment or _default_generate_enrichment

    try:
        raw_payload = generator(
            bundle_path=bundle_path,
            route=route,
            metadata_text=metadata_text,
            content_text=content_text,
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("Enrichment generator must return a dict payload")
        normalized_payload = _normalize_generated_payload(raw_payload)
        _write_sidecar_result(
            bundle_path,
            status="completed",
            provider=provider,
            model=model,
            failure_reason="",
            started_at=started_at,
            completed_at=now_iso(),
            payload=normalized_payload,
        )
        return _build_result(root, bundle_path, status="completed", reason="", provider=provider, model=model)
    except Exception as exc:
        return _record_failed_bundle(
            root,
            bundle_path,
            provider=provider,
            model=model,
            reason=str(exc) or exc.__class__.__name__,
            started_at=started_at,
        )


def process_pending_enrichment(
    root: Path,
    config_path: Path,
    *,
    generate_enrichment: Optional[Callable[..., Dict[str, Any]]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    state_path = default_enrichment_state_path(root)
    state_payload = _load_json_dict(state_path, preserve_corrupt=True)
    pending_bundles = state_payload.get("pending_bundles")
    if not isinstance(pending_bundles, list):
        pending_bundles = []

    settings = load_config(config_path)
    processed = 0
    completed = 0
    deferred = 0
    failed = 0
    results: List[Dict[str, Any]] = []
    retained_entries: List[Dict[str, Any]] = []

    for entry in pending_bundles:
        if not isinstance(entry, dict):
            continue

        if limit is not None and processed >= limit:
            retained_entries.append(entry)
            continue

        bundle_path_text = str(entry.get("bundle_path") or "").strip()
        if not bundle_path_text:
            continue

        bundle_path = root / bundle_path_text
        try:
            result = enrich_bundle(root, bundle_path, settings, generate_enrichment=generate_enrichment)
        except Exception as exc:
            result = _record_failed_bundle(
                root,
                bundle_path,
                provider="",
                model="",
                reason=str(exc) or exc.__class__.__name__,
                write_sidecar=bundle_path.exists(),
            )
        processed += 1
        results.append(result)

        if result["status"] == "completed":
            completed += 1
            continue

        retained_entry = {
            "bundle_path": bundle_path_text,
            "status": result["status"],
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "failure_reason": result.get("failure_reason", ""),
            "queued_at": str(entry.get("queued_at") or now_iso()),
            "updated_at": now_iso(),
        }
        retained_entries.append(retained_entry)
        if result["status"] == "deferred":
            deferred += 1
        else:
            failed += 1

    state_payload["pending_bundles"] = retained_entries
    timestamp = now_iso()
    state_payload.setdefault("created_at", timestamp)
    state_payload["updated_at"] = timestamp
    _write_json_atomic(state_path, state_payload)

    return {
        "processed": processed,
        "completed": completed,
        "deferred": deferred,
        "failed": failed,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process queued raw enrichment bundles.")
    parser.add_argument("--root", default=".", help="Vault root containing 00_System and 20_Raw")
    parser.add_argument("--config", default="", help="Workbench config path")
    parser.add_argument("--limit", type=int, default=None, help="Maximum pending bundles to process")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config_path = (
        Path(args.config).expanduser().resolve()
        if args.config
        else Path.home() / ".config" / "infinite_lore" / "workbench.json"
    )
    result = process_pending_enrichment(root, config_path, limit=args.limit)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
