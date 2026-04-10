from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def slugify(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered or "note"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_list_value(value: str) -> List[str]:
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        parts = re.findall(r'"([^"]*)"|([^,\s][^,]*)', inner)
        results: List[str] = []
        for quoted, bare in parts:
            item = quoted or bare.strip()
            if item:
                results.append(item)
        return results
    return [value]


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    metadata: Dict[str, object] = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == "---":
            body = "\n".join(lines[index + 1 :]).lstrip("\n")
            return metadata, body
        if not line.strip():
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value.startswith("[") and value.endswith("]"):
            metadata[key] = parse_list_value(value)
        else:
            metadata[key] = value
        index += 1
    return metadata, ""


def dump_value(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(yaml_quote(str(item)) for item in value) + "]"
    return str(value)


def build_frontmatter(metadata: Dict[str, object]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {dump_value(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def read_note(path: Path) -> Tuple[Dict[str, object], str]:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def write_note(path: Path, metadata: Dict[str, object], body: str) -> None:
    path.write_text(build_frontmatter(metadata) + body.strip() + "\n", encoding="utf-8")


def extract_title_and_paragraphs(content: str) -> Tuple[str, List[str], List[str]]:
    title = ""
    headings: List[str] = []
    paragraphs: List[str] = []
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", content) if chunk.strip()]

    for chunk in chunks:
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        first = lines[0]
        heading_match = re.match(r"^#\s+(.+)$", first)
        subheading_match = re.match(r"^##+\s+(.+)$", first)
        if heading_match:
            if not title:
                title = heading_match.group(1).strip()
            else:
                headings.append(heading_match.group(1).strip())
            if len(lines) > 1:
                paragraphs.append(" ".join(lines[1:]))
            continue
        if subheading_match:
            headings.append(subheading_match.group(1).strip())
            if len(lines) > 1:
                paragraphs.append(" ".join(lines[1:]))
            continue
        paragraphs.append(" ".join(lines))

    if not title:
        title = "Untitled Source"
    return title, headings, paragraphs


def extract_questions(paragraphs: List[str]) -> List[str]:
    questions: List[str] = []
    for paragraph in paragraphs:
        for line in re.split(r"(?<=[?])\s+", paragraph):
            candidate = line.strip()
            if candidate.endswith("?") and candidate not in questions:
                questions.append(candidate)
    return questions


def classify_heading(heading: str) -> Tuple[str, str]:
    slug = slugify(heading)
    lowered = heading.lower()
    if heading.endswith("?"):
        return "question", slug
    if any(keyword in lowered for keyword in ("framework", "model", "loop", "system", "method", "strategy", "process")):
        return "framework", slug
    return "concept", slug


def unique_candidates(title: str, headings: List[str], questions: List[str]) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    seen = set()

    for question in questions:
        note_type = "question"
        slug = slugify(question.rstrip("?"))
        key = (note_type, slug)
        if key not in seen:
            candidates.append({"note_type": note_type, "title": question, "slug": slug})
            seen.add(key)

    if title and not title.endswith("?"):
        note_type, slug = classify_heading(title)
        key = (note_type, slug)
        if key not in seen:
            candidates.append({"note_type": note_type, "title": title, "slug": slug})
            seen.add(key)

    for heading in headings:
        note_type, slug = classify_heading(heading)
        key = (note_type, slug)
        if key not in seen:
            candidates.append({"note_type": note_type, "title": heading, "slug": slug})
            seen.add(key)

    return candidates[:3]


def build_synthesis_body(
    summary: str,
    key_points: List[str],
    reusable_ideas: List[str],
    related_domains: List[str],
    questions: List[str],
    raw_bundle_ref: str,
    content_ref: str,
) -> str:
    reusable_block = "\n".join(f"- {idea}" for idea in reusable_ideas) if reusable_ideas else "- No reusable ideas extracted yet."
    key_points_block = "\n".join(f"- {point}" for point in key_points) if key_points else "- No key points extracted."
    candidate_links_block = "\n".join(f"- Related domain: {domain}" for domain in related_domains) if related_domains else "- No candidate links yet."
    questions_block = "\n".join(f"- {question}" for question in questions) if questions else "- No explicit open questions extracted from source."
    return (
        "# Synthesis\n\n"
        "## Source Summary\n"
        f"{summary}\n\n"
        "## Key Points\n"
        f"{key_points_block}\n\n"
        "## Reusable Ideas\n"
        f"{reusable_block}\n\n"
        "## Candidate Links\n"
        f"{candidate_links_block}\n\n"
        "## Open Questions\n"
        f"{questions_block}\n\n"
        "## Source Lineage\n"
        f"- Raw bundle: `{raw_bundle_ref}`\n"
        f"- Content: `{content_ref}`\n"
    )


def make_synthesis_metadata(
    title: str,
    domain: str,
    related_domains: List[str],
    privacy: str,
    source_refs: List[str],
    confidence: str,
    raw_bundle_ref: str,
    compiled_from: str,
    note_id: str,
) -> Dict[str, object]:
    timestamp = now_iso()
    return {
        "id": note_id,
        "title": title,
        "layer": "wiki",
        "note_type": "synthesis",
        "primary_domain": domain,
        "related_domains": related_domains,
        "privacy": privacy,
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "source_refs": source_refs,
        "confidence": confidence,
        "last_compiled_at": timestamp,
        "last_reviewed_at": "",
        "raw_bundle_ref": raw_bundle_ref,
        "compiled_from": compiled_from,
    }


def make_small_note_metadata(
    note_id: str,
    title: str,
    note_type: str,
    domain: str,
    privacy: str,
    source_refs: List[str],
    raw_bundle_ref: str,
    compiled_from: str,
) -> Dict[str, object]:
    timestamp = now_iso()
    return {
        "id": note_id,
        "title": title,
        "layer": "wiki",
        "note_type": note_type,
        "primary_domain": domain,
        "related_domains": [],
        "privacy": privacy,
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "source_refs": source_refs,
        "confidence": "medium",
        "last_compiled_at": timestamp,
        "last_reviewed_at": "",
        "raw_bundle_ref": raw_bundle_ref,
        "compiled_from": compiled_from,
    }


def build_small_note_body(note_type: str, title: str, evidence: str, raw_bundle_ref: str, synthesis_ref: str) -> str:
    if note_type == "question":
        middle_section = f"## Question\n{title}\n\n## Why It Matters\n{evidence}\n"
    elif note_type == "framework":
        middle_section = f"## Framework Summary\n{evidence}\n"
    else:
        middle_section = f"## Definition\n{evidence}\n"
    return (
        f"# {title}\n\n"
        f"{middle_section}\n"
        "## Supporting Evidence\n"
        f"- {evidence}\n\n"
        "## Source Lineage\n"
        f"- Raw bundle: `{raw_bundle_ref}`\n"
        f"- Synthesis: `{synthesis_ref}`\n"
    )


def append_unique_line(block: str, line: str) -> str:
    if line in block:
        return block
    if not block.endswith("\n"):
        block += "\n"
    return block + line + "\n"


def merge_small_note(existing_path: Path, raw_bundle_ref: str, synthesis_ref: str, source_ref: str, evidence: str) -> None:
    metadata, body = read_note(existing_path)
    source_refs = list(metadata.get("source_refs", []))
    if source_ref not in source_refs:
        source_refs.append(source_ref)
    metadata["source_refs"] = source_refs
    metadata["updated_at"] = now_iso()
    metadata["last_compiled_at"] = now_iso()

    if "## Supporting Evidence\n" in body:
        head, tail = body.split("## Supporting Evidence\n", 1)
        if "## Source Lineage\n" in tail:
            evidence_block, lineage_block = tail.split("## Source Lineage\n", 1)
        else:
            evidence_block, lineage_block = tail, ""
        evidence_block = append_unique_line(evidence_block.strip() + "\n", f"- {evidence}")
        lineage_block = append_unique_line(lineage_block.strip() + "\n", f"- Raw bundle: `{raw_bundle_ref}`")
        lineage_block = append_unique_line(lineage_block, f"- Synthesis: `{synthesis_ref}`")
        body = head + "## Supporting Evidence\n" + evidence_block.rstrip() + "\n\n## Source Lineage\n" + lineage_block.rstrip() + "\n"
    else:
        body = body.rstrip() + f"\n\n## Supporting Evidence\n- {evidence}\n\n## Source Lineage\n- Raw bundle: `{raw_bundle_ref}`\n- Synthesis: `{synthesis_ref}`\n"

    write_note(existing_path, metadata, body)


def update_domain_index(index_path: Path, synthesis_path: str, title: str) -> None:
    content = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    marker = "## Recently Compiled"
    link_line = f"- [[{synthesis_path}|{title}]]"

    if marker not in content:
        content = content.rstrip() + f"\n\n{marker}\n\n{link_line}\n"
    elif link_line not in content:
        before, after = content.split(marker, 1)
        after = after.lstrip("\n")
        content = before.rstrip() + f"\n\n{marker}\n\n{link_line}\n"
        if after.strip():
            content += "\n" + after.strip() + "\n"

    index_path.write_text(content, encoding="utf-8")


def update_bundle_metadata(bundle_path: Path, compiled_note_refs: List[str]) -> None:
    metadata_path = bundle_path / "metadata.md"
    metadata, body = read_note(metadata_path)
    metadata["compiled_at"] = now_iso()
    metadata["compiled_note_refs"] = compiled_note_refs
    metadata["updated_at"] = now_iso()
    write_note(metadata_path, metadata, body)


def compile_bundle(root: Path, bundle_path: Path) -> Dict[str, object]:
    metadata, _ = read_note(bundle_path / "metadata.md")
    content = (bundle_path / "content.md").read_text(encoding="utf-8")

    domain = str(metadata.get("primary_domain", "")).strip()
    if not domain:
        raise ValueError("Bundle metadata is missing primary_domain")
    if metadata.get("conversion_status") == "failed":
        raise ValueError("Cannot compile a failed raw bundle")

    title, headings, paragraphs = extract_title_and_paragraphs(content)
    questions = extract_questions(paragraphs)
    candidates = unique_candidates(title, headings, questions)

    source_slug = slugify(title)
    privacy = str(metadata.get("privacy", "private") or "private")
    related_domains = list(metadata.get("related_domains", []))
    raw_bundle_ref = bundle_path.relative_to(root).as_posix()
    content_ref = (bundle_path / "content.md").relative_to(root).as_posix()
    source_refs = list(metadata.get("source_refs", []))
    confidence = str(metadata.get("extraction_confidence", "medium") or "medium")

    wiki_dir = root / "30_Wiki" / domain
    wiki_dir.mkdir(parents=True, exist_ok=True)
    synthesis_filename = f"{source_slug}--synthesis.md"
    synthesis_path = wiki_dir / synthesis_filename
    synthesis_rel = synthesis_path.relative_to(root).as_posix()
    summary = paragraphs[0] if paragraphs else title
    key_points = paragraphs[:3] if paragraphs else [title]
    reusable_ideas = [candidate["title"] for candidate in candidates if candidate["note_type"] != "question"][:3]
    synthesis_body = build_synthesis_body(summary, key_points, reusable_ideas, related_domains, questions, raw_bundle_ref, content_ref)
    synthesis_metadata = make_synthesis_metadata(
        title=title,
        domain=domain,
        related_domains=related_domains,
        privacy=privacy,
        source_refs=source_refs,
        confidence=confidence,
        raw_bundle_ref=raw_bundle_ref,
        compiled_from=content_ref,
        note_id=synthesis_filename[:-3],
    )
    write_note(synthesis_path, synthesis_metadata, synthesis_body)

    small_note_paths: List[str] = []
    for candidate in candidates:
        note_type = candidate["note_type"]
        slug = candidate["slug"]
        candidate_title = candidate["title"]
        if note_type == "concept" and slug == slugify(title):
            # Allow the title concept, but only if there is enough descriptive body text.
            if not paragraphs:
                continue
        evidence = paragraphs[0] if paragraphs else candidate_title
        existing_matches = sorted(wiki_dir.glob(f"*--{note_type}--{slug}.md"))
        if existing_matches:
            target = existing_matches[0]
            merge_small_note(target, raw_bundle_ref, synthesis_rel, source_refs[0] if source_refs else raw_bundle_ref, evidence)
            small_note_paths.append(target.relative_to(root).as_posix())
            continue

        filename = f"{source_slug}--{note_type}--{slug}.md"
        target = wiki_dir / filename
        note_metadata = make_small_note_metadata(
            note_id=filename[:-3],
            title=candidate_title,
            note_type=note_type,
            domain=domain,
            privacy=privacy,
            source_refs=source_refs,
            raw_bundle_ref=raw_bundle_ref,
            compiled_from=synthesis_rel,
        )
        note_body = build_small_note_body(note_type, candidate_title, evidence, raw_bundle_ref, synthesis_rel)
        write_note(target, note_metadata, note_body)
        small_note_paths.append(target.relative_to(root).as_posix())

    compiled_refs = [synthesis_rel] + small_note_paths
    update_bundle_metadata(bundle_path, compiled_refs)
    index_path = root / "10_Domains" / domain / "index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text(f"# {domain}\n", encoding="utf-8")
    update_domain_index(index_path, synthesis_rel, title)

    from tools.relation_index import save_relation_index

    save_relation_index(root)

    return {
        "synthesis_path": synthesis_rel,
        "small_note_paths": small_note_paths,
        "compiled_note_refs": compiled_refs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a raw bundle into Infinite Lore wiki notes.")
    parser.add_argument("--bundle", required=True, help="Path to raw bundle")
    parser.add_argument("--root", default=".", help="Vault root path")
    args = parser.parse_args()

    result = compile_bundle(Path(args.root), Path(args.bundle))
    print(result["synthesis_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
