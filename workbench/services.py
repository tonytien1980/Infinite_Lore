from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

from tools.health_check import check_vault
from tools.import_bundle import import_source
from tools.raw_enrichment import default_enrichment_state_path
from tools.wiki_compile import compile_bundle, parse_frontmatter
from workbench.source_store import load_source_state, summarize_source_state


def _bundle_paths(vault_root: Path) -> List[Path]:
    inbox = vault_root / "20_Raw/inbox"
    if not inbox.exists():
        return []
    return sorted([path for path in inbox.iterdir() if path.is_dir()], key=lambda item: item.name, reverse=True)


def _knowledge_paths(vault_root: Path) -> List[Path]:
    wiki_root = vault_root / "30_Wiki"
    if not wiki_root.exists():
        return []
    return sorted(wiki_root.rglob("*.md"))


def _read_frontmatter(path: Path) -> Dict[str, object]:
    metadata, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    return metadata


def _list_of_strings(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _read_enrichment_payload(bundle_path: Path) -> Dict[str, object]:
    enrichment_path = bundle_path / "enrichment.json"
    empty_payload: Dict[str, object] = {
        "enrichment_status": "",
        "enrichment_provider": "",
        "enrichment_model": "",
        "enrichment_failure_reason": "",
        "enrichment_updated_at": "",
        "enrichment_summary": "",
        "enrichment_primary_domain_suggestion": "",
        "enrichment_related_domains_suggestion": [],
        "enrichment_topic_tags": [],
        "enrichment_entity_hints": [],
        "enrichment_status_reason": "",
    }
    if not enrichment_path.exists():
        return empty_payload

    try:
        payload = json.loads(enrichment_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return empty_payload

    if not isinstance(payload, dict):
        return empty_payload

    return {
        "enrichment_status": str(payload.get("status", "") or ""),
        "enrichment_provider": str(payload.get("provider", "") or ""),
        "enrichment_model": str(payload.get("model", "") or ""),
        "enrichment_failure_reason": str(payload.get("failure_reason", "") or ""),
        "enrichment_updated_at": str(payload.get("updated_at", "") or ""),
        "enrichment_summary": str(payload.get("summary", "") or ""),
        "enrichment_primary_domain_suggestion": str(payload.get("primary_domain_suggestion", "") or ""),
        "enrichment_related_domains_suggestion": _list_of_strings(payload.get("related_domains_suggestion")),
        "enrichment_topic_tags": _list_of_strings(payload.get("topic_tags")),
        "enrichment_entity_hints": _list_of_strings(payload.get("entity_hints")),
        "enrichment_status_reason": str(payload.get("status_reason") or payload.get("failure_reason") or ""),
    }


def _active_enrichment_bundle_paths(vault_root: Path) -> Set[str]:
    state_path = default_enrichment_state_path(vault_root)
    if not state_path.exists():
        return set()

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return set()

    if not isinstance(payload, dict):
        return set()

    pending_bundles = payload.get("pending_bundles")
    if not isinstance(pending_bundles, list):
        return set()

    active_paths: Set[str] = set()
    for entry in pending_bundles:
        if not isinstance(entry, dict):
            continue
        bundle_path = str(entry.get("bundle_path") or "").strip()
        if bundle_path:
            active_paths.add(bundle_path)
    return active_paths


DOMAIN_KEYWORDS = {
    "business-strategy": ["strategy", "positioning", "advantage", "moat", "business"],
    "management": ["team", "manager", "management", "leadership", "decision"],
    "marketing-acquisition": ["marketing", "acquisition", "funnel", "campaign", "audience"],
    "finance-investing": ["finance", "investing", "valuation", "market", "cashflow"],
    "ai-application": ["ai", "llm", "model", "prompt", "automation", "knowledge"],
    "consulting": ["client", "consulting", "proposal", "delivery", "engagement"],
    "personal": ["journal", "reflection", "life", "energy", "personal"],
}


def infer_domains(source_name: str, content_text: str) -> Tuple[str, List[str]]:
    text = f"{source_name}\n{content_text}".lower()
    scored: List[Tuple[str, int]] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        scored.append((domain, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    primary = scored[0][0] if scored and scored[0][1] > 0 else "ai-application"
    related = [domain for domain, score in scored[1:] if score > 0]
    return primary, related


def get_dashboard(vault_root: Path) -> Dict[str, object]:
    bundles = _bundle_paths(vault_root)
    knowledge = list_knowledge(vault_root)
    warnings = 0
    recent_imports = []
    for bundle in bundles[:5]:
        metadata_path = bundle / "metadata.md"
        if metadata_path.exists():
            metadata = _read_frontmatter(metadata_path)
            enrichment = _read_enrichment_payload(bundle)
            if metadata.get("review_required") == "true":
                warnings += 1
            recent_imports.append(
                {
                    "bundle_path": bundle.relative_to(vault_root).as_posix(),
                    "title": metadata.get("title") or bundle.name,
                    "primary_domain": metadata.get("primary_domain", ""),
                    "conversion_status": metadata.get("conversion_status", ""),
                    "enrichment_status": enrichment["enrichment_status"],
                    "enrichment_updated_at": enrichment["enrichment_updated_at"],
                }
            )

    return {
        "bundle_count": len(bundles),
        "knowledge_count": len(knowledge["synthesis"]) + len(knowledge["small_notes"]),
        "warning_count": warnings,
        "recent_imports": recent_imports,
        "recent_synthesis": knowledge["synthesis"][:5],
        "recent_small_notes": knowledge["small_notes"][:5],
    }


def list_bundles(vault_root: Path) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    active_enrichment_bundle_paths = _active_enrichment_bundle_paths(vault_root)
    for bundle in _bundle_paths(vault_root):
        bundle_path_text = bundle.relative_to(vault_root).as_posix()
        metadata_path = bundle / "metadata.md"
        metadata = _read_frontmatter(metadata_path) if metadata_path.exists() else {}
        enrichment = _read_enrichment_payload(bundle)
        results.append(
            {
                "bundle_path": bundle_path_text,
                "title": metadata.get("title", bundle.name),
                "primary_domain": metadata.get("primary_domain", ""),
                "conversion_status": metadata.get("conversion_status", ""),
                "compiled_note_refs": metadata.get("compiled_note_refs", []),
                "review_required": metadata.get("review_required", "false"),
                "enrichment_status": enrichment["enrichment_status"],
                "enrichment_provider": enrichment["enrichment_provider"],
                "enrichment_model": enrichment["enrichment_model"],
                "enrichment_failure_reason": enrichment["enrichment_failure_reason"],
                "enrichment_updated_at": enrichment["enrichment_updated_at"],
                "enrichment_summary": enrichment["enrichment_summary"],
                "enrichment_primary_domain_suggestion": enrichment["enrichment_primary_domain_suggestion"],
                "enrichment_related_domains_suggestion": enrichment["enrichment_related_domains_suggestion"],
                "enrichment_topic_tags": enrichment["enrichment_topic_tags"],
                "enrichment_entity_hints": enrichment["enrichment_entity_hints"],
                "enrichment_status_reason": enrichment["enrichment_status_reason"],
                "enrichment_queue_active": bundle_path_text in active_enrichment_bundle_paths,
            }
        )
    return results


def list_knowledge(vault_root: Path) -> Dict[str, List[Dict[str, object]]]:
    synthesis: List[Dict[str, object]] = []
    small_notes: List[Dict[str, object]] = []

    for note_path in _knowledge_paths(vault_root):
        metadata = _read_frontmatter(note_path)
        note_type = metadata.get("note_type")
        if not note_type:
            continue
        entry = {
            "path": note_path.relative_to(vault_root).as_posix(),
            "title": metadata.get("title", note_path.stem),
            "note_type": note_type,
            "primary_domain": metadata.get("primary_domain", ""),
            "source_refs": metadata.get("source_refs", []),
        }
        if note_type == "synthesis":
            synthesis.append(entry)
        else:
            small_notes.append(entry)

    return {"synthesis": synthesis, "small_notes": small_notes}


def import_file(vault_root: Path, file_name: str, file_bytes: bytes, primary_domain: str | None = None) -> Dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        temp_path = Path(tmp) / file_name
        temp_path.write_bytes(file_bytes)
        content_text = file_bytes.decode("utf-8", errors="replace")
        inferred_primary, related_domains = infer_domains(file_name, content_text)
        selected_domain = primary_domain or inferred_primary
        bundle = import_source(vault_root, str(temp_path), selected_domain, related_domains)

    compile_result = compile_bundle(vault_root, bundle)
    return {
        "bundle_path": bundle.relative_to(vault_root).as_posix(),
        "primary_domain": selected_domain,
        "related_domains": related_domains,
        "compile": compile_result,
    }


def import_url(vault_root: Path, url: str, primary_domain: str | None = None) -> Dict[str, object]:
    inferred_primary, related_domains = infer_domains(url, url)
    selected_domain = primary_domain or inferred_primary
    bundle = import_source(vault_root, url, selected_domain, related_domains)
    compile_result = compile_bundle(vault_root, bundle)
    return {
        "bundle_path": bundle.relative_to(vault_root).as_posix(),
        "primary_domain": selected_domain,
        "related_domains": related_domains,
        "compile": compile_result,
    }


def get_health(vault_root: Path) -> Dict[str, object]:
    report = check_vault(vault_root)
    return {
        "status": "ok" if not report["errors"] else "issues",
        "errors": report["errors"],
    }


def get_system_info(vault_root: Path) -> Dict[str, str]:
    return {"vault_root": str(vault_root.resolve())}


def get_inbox_summary(source_state_path: Path) -> Dict[str, object]:
    return summarize_source_state(source_state_path)


def run_inbox_scan(vault_root: Path, source_state_path: Path) -> Dict[str, object]:
    from tools.automation_scan import run_scan

    state = load_source_state(source_state_path)
    configured_sources = state.get("sources", [])
    if not isinstance(configured_sources, list):
        configured_sources = []
    return run_scan(vault_root, configured_sources, source_state_path)
