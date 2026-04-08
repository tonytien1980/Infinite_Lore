from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from tools.health_check import check_vault
from tools.import_bundle import import_source
from tools.wiki_compile import compile_bundle, parse_frontmatter


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
            if metadata.get("review_required") == "true":
                warnings += 1
            recent_imports.append(
                {
                    "bundle_path": bundle.relative_to(vault_root).as_posix(),
                    "title": metadata.get("title") or bundle.name,
                    "primary_domain": metadata.get("primary_domain", ""),
                    "conversion_status": metadata.get("conversion_status", ""),
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
    for bundle in _bundle_paths(vault_root):
        metadata_path = bundle / "metadata.md"
        metadata = _read_frontmatter(metadata_path) if metadata_path.exists() else {}
        results.append(
            {
                "bundle_path": bundle.relative_to(vault_root).as_posix(),
                "title": metadata.get("title", bundle.name),
                "primary_domain": metadata.get("primary_domain", ""),
                "conversion_status": metadata.get("conversion_status", ""),
                "compiled_note_refs": metadata.get("compiled_note_refs", []),
                "review_required": metadata.get("review_required", "false"),
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
