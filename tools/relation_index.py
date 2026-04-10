from __future__ import annotations

import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from pathlib import PurePosixPath
from typing import Dict, Iterable, List, Tuple

from tools.wiki_compile import parse_frontmatter


RELATION_INDEX_PATH = Path("00_System/relation-index.json")
EXCLUDED_NOTE_TYPES = {
    "reflection-entry",
    "correction-proposal",
    "journal-entry",
    "project-log",
    "artifact",
    "artifacts",
}
EXCLUDED_LAYERS = {
    "artifact",
    "journal",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_ref(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    if not text:
        return ""
    return PurePosixPath(text).as_posix()


def as_string_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [normalize_ref(item) for item in value if normalize_ref(item)]
    if value in (None, ""):
        return []
    text = normalize_ref(value)
    return [text] if text else []


def read_wiki_note(path: Path) -> Tuple[Dict[str, object], str]:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def iter_compiled_wiki_notes(root: Path) -> Iterable[Path]:
    wiki_root = root / "30_Wiki"
    if not wiki_root.exists():
        return []
    return sorted(path for path in wiki_root.rglob("*.md") if path.is_file())


def collect_notes(root: Path) -> List[Dict[str, object]]:
    notes: List[Dict[str, object]] = []
    for path in iter_compiled_wiki_notes(root):
        metadata, _ = read_wiki_note(path)
        note_type = normalize_ref(metadata.get("note_type")).lower()
        layer = normalize_ref(metadata.get("layer")).lower()
        if not note_type or note_type in EXCLUDED_NOTE_TYPES or layer in EXCLUDED_LAYERS:
            continue

        notes.append(
            {
                "path": path.relative_to(root).as_posix(),
                "title": normalize_ref(metadata.get("title")),
                "note_type": note_type,
                "primary_domain": normalize_ref(metadata.get("primary_domain")),
                "source_refs": as_string_list(metadata.get("source_refs")),
                "raw_bundle_ref": normalize_ref(metadata.get("raw_bundle_ref")),
                "compiled_from": normalize_ref(metadata.get("compiled_from")),
            }
        )

    return sorted(notes, key=lambda note: note["path"])


def add_edge(
    edges: List[Dict[str, object]],
    seen: set,
    source_note: str,
    target_note: str,
    relation: str,
    confidence: str,
    evidence_type: str,
    evidence_ref: str,
    updated_at: str,
) -> None:
    key = (source_note, target_note, relation, confidence, evidence_type, evidence_ref)
    if key in seen:
        return
    seen.add(key)
    edges.append(
        {
            "source_note": source_note,
            "target_note": target_note,
            "relation": relation,
            "confidence": confidence,
            "evidence_type": evidence_type,
            "evidence_ref": evidence_ref,
            "updated_at": updated_at,
        }
    )


def edge_identity(edge: Dict[str, object]) -> Tuple[object, ...]:
    return (
        edge.get("source_note"),
        edge.get("target_note"),
        edge.get("relation"),
        edge.get("confidence"),
        edge.get("evidence_type"),
        edge.get("evidence_ref"),
    )


def extract_derived_from_edges(notes: List[Dict[str, object]], updated_at: str) -> List[Dict[str, object]]:
    edges: List[Dict[str, object]] = []
    seen: set = set()
    notes_by_path = {note["path"]: note for note in notes}

    for note in notes:
        compiled_from = normalize_ref(note.get("compiled_from"))
        if not compiled_from or compiled_from not in notes_by_path:
            continue
        if compiled_from == note["path"]:
            continue
        add_edge(
            edges,
            seen,
            source_note=note["path"],
            target_note=compiled_from,
            relation="derived-from",
            confidence="EXTRACTED",
            evidence_type="compiled_from",
            evidence_ref=compiled_from,
            updated_at=updated_at,
        )

    return edges


def extract_shares_source_edges(notes: List[Dict[str, object]], updated_at: str) -> List[Dict[str, object]]:
    edges: List[Dict[str, object]] = []
    seen: set = set()

    for left, right in combinations(notes, 2):
        shared_source_refs = sorted(set(left.get("source_refs", [])) & set(right.get("source_refs", [])))
        if shared_source_refs:
            source_note, target_note = sorted([left["path"], right["path"]])
            add_edge(
                edges,
                seen,
                source_note=source_note,
                target_note=target_note,
                relation="shares-source",
                confidence="INFERRED",
                evidence_type="source_refs",
                evidence_ref=shared_source_refs[0],
                updated_at=updated_at,
            )
            continue

        left_raw_bundle = normalize_ref(left.get("raw_bundle_ref"))
        right_raw_bundle = normalize_ref(right.get("raw_bundle_ref"))
        if left_raw_bundle and left_raw_bundle == right_raw_bundle:
            source_note, target_note = sorted([left["path"], right["path"]])
            add_edge(
                edges,
                seen,
                source_note=source_note,
                target_note=target_note,
                relation="shares-source",
                confidence="INFERRED",
                evidence_type="raw_bundle_ref",
                evidence_ref=left_raw_bundle,
                updated_at=updated_at,
            )

    return edges


def build_relation_index(root: Path) -> Dict[str, object]:
    generated_at = now_iso()
    notes = collect_notes(root)
    edges = extract_derived_from_edges(notes, generated_at)
    edges.extend(extract_shares_source_edges(notes, generated_at))
    edges.sort(key=lambda edge: (edge["relation"], edge["source_note"], edge["target_note"], edge["evidence_type"], edge["evidence_ref"]))
    return {
        "generated_at": generated_at,
        "notes": notes,
        "edges": edges,
    }


def save_relation_index(root: Path) -> Dict[str, object]:
    artifact = build_relation_index(root)
    target = root / RELATION_INDEX_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        existing_edge_keys = [edge_identity(edge) for edge in existing.get("edges", [])]
        artifact_edge_keys = [edge_identity(edge) for edge in artifact.get("edges", [])]
        if existing.get("notes") == artifact.get("notes") and existing_edge_keys == artifact_edge_keys:
            return existing
    target.write_text(json.dumps(artifact, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return artifact
