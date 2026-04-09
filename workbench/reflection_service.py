from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from tools.import_bundle import slugify
from tools.wiki_compile import parse_frontmatter


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def archive_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _frontmatter_scalar(value: object) -> str:
    if isinstance(value, str):
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        if "\n" in normalized:
            encoded = base64.b64encode(normalized.encode("utf-8")).decode("ascii")
            return f"base64:{encoded}"
        return normalized
    return str(value)


def _decode_frontmatter_scalar(value: object) -> object:
    if not isinstance(value, str) or not value.startswith("base64:"):
        return value

    encoded = value.removeprefix("base64:")
    try:
        return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return value


def _decode_frontmatter_metadata(metadata: Dict[str, object]) -> Dict[str, object]:
    decoded: Dict[str, object] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            decoded[key] = [_decode_frontmatter_scalar(item) for item in value]
        else:
            decoded[key] = _decode_frontmatter_scalar(value)
    return decoded


def render_frontmatter(metadata: Dict[str, object]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            formatted = ", ".join(f'"{_frontmatter_scalar(item)}"' for item in value)
            lines.append(f"{key}: [{formatted}]")
        else:
            lines.append(f"{key}: {_frontmatter_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def read_note(vault_root: Path, relative_path: str) -> Dict[str, object]:
    note_path = resolve_vault_path(vault_root, relative_path)
    metadata, body = parse_frontmatter(note_path.read_text(encoding="utf-8"))
    return {"path": relative_path, "metadata": _decode_frontmatter_metadata(metadata), "body": body}


def write_note(vault_root: Path, relative_path: str, metadata: Dict[str, object], body: str) -> None:
    note_path = resolve_vault_path(vault_root, relative_path)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(render_frontmatter(metadata) + "\n" + body.strip() + "\n", encoding="utf-8")


def full_note_text(metadata: Dict[str, object], body: str) -> str:
    return render_frontmatter(metadata) + "\n" + body.strip() + "\n"


def resolve_vault_path(vault_root: Path, relative_path: str) -> Path:
    base = vault_root.resolve()
    candidate = (base / relative_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError("path must stay inside the vault") from exc
    return candidate


def _selection_terms(text: str) -> List[str]:
    terms: List[str] = []
    seen = set()

    for term in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        if len(term) <= 2 or term in seen:
            continue
        seen.add(term)
        terms.append(term)

    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        run_length = len(run)
        if run_length < 2:
            continue
        max_width = min(4, run_length)
        for width in range(2, max_width + 1):
            for start in range(0, run_length - width + 1):
                term = run[start : start + width]
                if term in seen:
                    continue
                seen.add(term)
                terms.append(term)

    return terms


def _score_grounding_note(selection_terms: List[str], note: Dict[str, object]) -> Tuple[int, int]:
    title = str(note.get("title", "")).lower()
    body = str(note.get("body", "")).lower()
    path = str(note.get("path", "")).lower()
    note_type = str(note.get("note_type", "")).lower()
    score = 0
    for term in selection_terms:
        if term in title:
            score += 4
        if term in body:
            score += 2
        if term in path:
            score += 1
    if note_type == "synthesis":
        score += 1
    return score, -int(note.get("_index", 0))


def pick_primary_grounding_note(
    vault_root: Path,
    ask_question: str,
    grounding: List[Dict[str, object]],
    raw_input: str = "",
) -> Dict[str, object]:
    if not grounding:
        raise ValueError("grounding is required")

    ranked: List[Tuple[Tuple[int, int], Dict[str, object]]] = []
    selection_terms = _selection_terms(f"{ask_question}\n{raw_input}")
    for index, candidate in enumerate(grounding):
        path = str(candidate["path"])
        try:
            loaded = read_note(vault_root, path)
            metadata = dict(loaded["metadata"])
            body = str(loaded["body"])
        except FileNotFoundError:
            metadata = {}
            body = str(candidate.get("body", ""))

        merged = {
            "path": path,
            "_index": index,
            "title": candidate.get("title") or metadata.get("title") or Path(path).stem,
            "note_type": candidate.get("note_type") or metadata.get("note_type") or "",
            "primary_domain": candidate.get("primary_domain") or metadata.get("primary_domain") or "unclassified",
            "source_refs": candidate.get("source_refs") or metadata.get("source_refs", []),
            "body": candidate.get("body") or body,
        }
        ranked.append((_score_grounding_note(selection_terms, merged), merged))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = dict(ranked[0][1])
    selected.pop("_index", None)
    return selected


def draft_reflection(
    vault_root: Path,
    ask_question: str,
    ask_mode: str,
    raw_input: str,
    grounding: List[Dict[str, object]],
) -> Dict[str, object]:
    linked_note = pick_primary_grounding_note(vault_root, ask_question, grounding, raw_input)
    created_at = now_timestamp()
    title = f"Reflection - {linked_note['title']}"
    body = (
        "# Reflection\n\n"
        "## Triggering Question\n"
        f"{ask_question}\n\n"
        "## My Interpretation\n"
        f"{raw_input}\n\n"
        "## Linked Context\n"
        f"- Linked note: `{linked_note['path']}`\n"
    )
    return {
        "id": f"reflection-{slugify(str(linked_note['title']))}-{archive_stamp()}",
        "title": title,
        "layer": "brainstorming",
        "note_type": "reflection-entry",
        "primary_domain": linked_note.get("primary_domain", "unclassified"),
        "related_domains": [],
        "privacy": "private",
        "status": "active",
        "created_at": created_at,
        "updated_at": created_at,
        "linked_note_ref": linked_note["path"],
        "linked_note_title": linked_note["title"],
        "ask_question": ask_question,
        "ask_mode": ask_mode,
        "grounding_note_refs": [item["path"] for item in grounding],
        "source_refs": [],
        "reflection_kind": "interpretation",
        "raw_input": raw_input,
        "body": body,
    }


def save_reflection(vault_root: Path, draft: Dict[str, object]) -> Dict[str, str]:
    domain = str(draft.get("primary_domain") or "unclassified")
    filename = f"{slugify(str(draft['linked_note_title']))}--reflection--{archive_stamp()}.md"
    relative_path = f"50_Brainstorming/reflections/{domain}/{filename}"
    allowed_keys = {
        "id",
        "title",
        "layer",
        "note_type",
        "primary_domain",
        "related_domains",
        "privacy",
        "status",
        "created_at",
        "updated_at",
        "linked_note_ref",
        "linked_note_title",
        "ask_question",
        "ask_mode",
        "grounding_note_refs",
        "source_refs",
        "reflection_kind",
        "raw_input",
    }
    metadata = {key: value for key, value in draft.items() if key in allowed_keys}
    write_note(vault_root, relative_path, metadata, str(draft["body"]))
    return {"path": relative_path}


def _extract_replacements(raw_input: str) -> List[Tuple[str, str]]:
    patterns = [
        r"(?:把|將|将)?\s*(?P<old>.+?)\s*(?:改成|改為|改为|替換成|替换成)\s*(?P<new>.+)",
        r"replace\s+(?P<old>.+?)\s+with\s+(?P<new>.+)",
        r"change\s+(?P<old>.+?)\s+to\s+(?P<new>.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_input, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        old = match.group("old").strip(" \t\r\n`'\"，。.!?！？")
        new = match.group("new").strip(" \t\r\n`'\"，。.!?！？")
        if old and new:
            return [(old, new)]
    return []


def _rewrite_body_from_issue(current_body: str, raw_input: str) -> str:
    cleaned = " ".join(raw_input.split()).strip()
    if not cleaned:
        return current_body

    summary_match = re.search(r"(^## Source Summary\n)(.*?)(?=\n## |\Z)", current_body, re.DOTALL | re.MULTILINE)
    if summary_match:
        summary_text = summary_match.group(2).strip()
        if summary_text:
            summary_line = " ".join(summary_text.split())
            if summary_line[-1:] not in {".", "!", "?", "。", "！", "？"}:
                summary_line += "."
            revised_summary = f"{summary_line} This revision should emphasize: {cleaned}."
            return current_body[: summary_match.start(2)] + revised_summary + current_body[summary_match.end(2) :]

    paragraphs = current_body.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        stripped = paragraph.strip()
        if not stripped or stripped.startswith("# "):
            continue
        paragraphs[index] = stripped.rstrip() + f"\n\nThis revision should emphasize: {cleaned}."
        return "\n\n".join(paragraphs)

    return current_body.rstrip() + f"\n\nThis revision should emphasize: {cleaned}.\n"


def _build_proposed_body(current_body: str, raw_input: str) -> str:
    corrected = current_body
    for old, new in _extract_replacements(raw_input):
        corrected = corrected.replace(old, new)
    if corrected != current_body:
        return corrected

    return _rewrite_body_from_issue(current_body, raw_input)


def draft_correction(
    vault_root: Path,
    ask_question: str,
    ask_mode: str,
    raw_input: str,
    grounding: List[Dict[str, object]],
) -> Dict[str, object]:
    target_note = pick_primary_grounding_note(vault_root, ask_question, grounding, raw_input)
    note = read_note(vault_root, target_note["path"])
    created_at = now_timestamp()
    proposed_body = _build_proposed_body(str(note["body"]), raw_input)
    proposed_content = full_note_text(note["metadata"], proposed_body)
    proposal_body = (
        "# Correction Proposal\n\n"
        "## Triggering Question\n"
        f"{ask_question}\n\n"
        "## Reported Issue\n"
        f"{raw_input}\n\n"
        "## Proposed Change\n"
        f"{proposed_content}\n\n"
        "## Evidence\n"
        f"- Target note: `{target_note['path']}`\n"
    )
    proposal = {
        "id": f"correction-{slugify(str(target_note['title']))}-{archive_stamp()}",
        "title": f"Correction Proposal - {target_note['title']}",
        "layer": "brainstorming",
        "note_type": "correction-proposal",
        "primary_domain": target_note.get("primary_domain", "unclassified"),
        "related_domains": [],
        "privacy": "private",
        "status": "pending",
        "created_at": created_at,
        "updated_at": created_at,
        "target_note_ref": target_note["path"],
        "target_note_title": target_note["title"],
        "ask_question": ask_question,
        "ask_mode": ask_mode,
        "grounding_note_refs": [item["path"] for item in grounding],
        "source_refs": [],
        "proposal_status": "pending",
        "proposal_kind": "correction",
        "archive_version_ref": "",
        "applied_at": "",
        "reported_issue": raw_input,
        "proposed_content": proposed_content,
        "body": proposal_body,
    }
    save_correction_draft(vault_root, proposal)
    return proposal


def _proposal_path(domain: str, proposal: Dict[str, object], status: str) -> str:
    title = str(proposal.get("target_note_title") or proposal.get("title") or "correction")
    filename = f"{slugify(title)}--correction--{archive_stamp()}.md"
    return f"50_Brainstorming/corrections/{status}/{domain}/{filename}"


def _proposal_metadata(proposal: Dict[str, object]) -> Dict[str, object]:
    return {
        key: value
        for key, value in proposal.items()
        if key not in {"body", "proposed_content", "reported_issue"}
    }


def _proposal_body(proposal: Dict[str, object], decision: str) -> str:
    return (
        "# Correction Proposal\n\n"
        "## Triggering Question\n"
        f"{proposal['ask_question']}\n\n"
        "## Reported Issue\n"
        f"{proposal['reported_issue']}\n\n"
        "## Proposed Change\n"
        f"{proposal['proposed_content']}\n\n"
        "## Evidence\n"
        f"- Target note: `{proposal['target_note_ref']}`\n\n"
        "## Decision\n"
        f"- {decision}\n"
    )


def _write_proposal_record(vault_root: Path, proposal: Dict[str, object], status: str, decision: str) -> str:
    domain = str(proposal.get("primary_domain") or "unclassified")
    relative_path = _proposal_path(domain, proposal, status)
    metadata = _proposal_metadata(proposal)
    metadata["status"] = status
    metadata["proposal_status"] = status
    metadata["updated_at"] = now_timestamp()
    if status == "applied":
        metadata["archive_version_ref"] = proposal["archive_version_ref"]
        metadata["applied_at"] = proposal["applied_at"]
    write_note(vault_root, relative_path, metadata, _proposal_body(proposal, decision))
    return relative_path


def _extract_section(body: str, heading: str, next_heading: str) -> str:
    pattern = rf"{re.escape(heading)}\n(.*?)(?=\n\n{re.escape(next_heading)}\n)"
    match = re.search(pattern, body, re.DOTALL)
    return match.group(1).rstrip() if match else ""


def _load_pending_proposal(vault_root: Path, proposal: Dict[str, object]) -> Dict[str, object]:
    proposal_path = str(proposal.get("proposal_path", "")).strip()
    if not proposal_path or not proposal_path.startswith("50_Brainstorming/corrections/pending/"):
        raise ValueError("a pending proposal is required before applying a correction")

    note_path = resolve_vault_path(vault_root, proposal_path)
    if not note_path.exists():
        raise ValueError("a pending proposal is required before applying a correction")

    metadata, body = parse_frontmatter(note_path.read_text(encoding="utf-8"))
    if metadata.get("proposal_status") != "pending" or metadata.get("proposal_kind") != "correction":
        raise ValueError("a pending proposal is required before applying a correction")

    loaded: Dict[str, object] = dict(metadata)
    loaded["proposal_path"] = proposal_path
    loaded["body"] = body
    loaded["reported_issue"] = str(
        proposal.get("reported_issue") or _extract_section(body, "## Reported Issue", "## Proposed Change")
    )
    loaded["proposed_content"] = str(
        proposal.get("proposed_content") or _extract_section(body, "## Proposed Change", "## Evidence")
    )
    return loaded


def apply_correction(vault_root: Path, proposal: Dict[str, object]) -> Dict[str, str]:
    resolved = _load_pending_proposal(vault_root, proposal)
    resolved["proposed_content"] = str(proposal.get("proposed_content") or resolved["proposed_content"])

    target_path = resolve_vault_path(vault_root, str(resolved["target_note_ref"]))
    domain = str(resolved.get("primary_domain") or "unclassified")
    archive_name = f"{slugify(str(resolved['target_note_title']))}--before-correction--{archive_stamp()}.md"
    archive_relative = f"80_Archive/wiki-versions/{domain}/{archive_name}"
    archive_path = resolve_vault_path(vault_root, archive_relative)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")

    target_path.write_text(str(resolved["proposed_content"]).rstrip() + "\n", encoding="utf-8")

    resolved["proposal_status"] = "applied"
    resolved["status"] = "applied"
    resolved["archive_version_ref"] = archive_relative
    resolved["applied_at"] = now_timestamp()
    original_pending_path = str(resolved.get("proposal_path", ""))
    applied_relative = _write_proposal_record(vault_root, resolved, "applied", "applied")
    resolved["proposal_path"] = applied_relative

    if original_pending_path:
        pending_path = resolve_vault_path(vault_root, original_pending_path)
        if pending_path.exists():
            pending_path.unlink()

    return {"archive_version_ref": archive_relative, "proposal_path": applied_relative}


def save_correction_draft(vault_root: Path, proposal: Dict[str, object]) -> Dict[str, str]:
    domain = str(proposal.get("primary_domain") or "unclassified")
    relative_path = _proposal_path(domain, proposal, "pending")
    proposal["proposal_path"] = relative_path
    write_note(vault_root, relative_path, _proposal_metadata(proposal), _proposal_body(proposal, "pending"))
    return {"proposal_path": relative_path}
