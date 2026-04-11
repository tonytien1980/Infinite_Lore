from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from tools.wiki_compile import parse_frontmatter
from workbench.provider_router import resolve_route_provider

RELATION_INDEX_PATH = Path("00_System/relation-index.json")
SUPPORTED_NOTE_TYPES = {"synthesis", "concept", "framework", "question", "reference"}
RELATION_CONFIDENCE_BONUS = {
    "EXTRACTED": 3,
    "INFERRED": 1,
}
SUPPORTED_RELATIONS = {"derived-from", "shares-source"}
INSUFFICIENT_GROUNDED_ANSWER = "目前知識庫中沒有足夠可依據的內容，無法有把握地回答這個問題。"
INSUFFICIENT_GROUNDED_LIMIT = "目前知識庫中的可用證據不足。"

QUERY_PATTERNS = [
    "what notes do i have",
    "list",
    "show",
    "which notes",
    "find",
]

ASK_PATTERNS = [
    "what is",
    "summarize",
    "compare",
    "explain",
    "what does my library currently say about",
]

STOPWORDS = {
    "what",
    "does",
    "my",
    "have",
    "about",
    "library",
    "know",
    "knows",
    "the",
    "and",
    "for",
    "into",
    "from",
    "this",
    "that",
    "with",
    "your",
    "current",
    "currently",
    "show",
    "list",
    "find",
    "notes",
}


def infer_mode(question: str, requested_mode: str) -> str:
    if requested_mode in {"ask", "query"}:
        return requested_mode

    lowered = question.lower()
    if any(pattern in lowered for pattern in QUERY_PATTERNS):
        return "query"
    if any(pattern in lowered for pattern in ASK_PATTERNS):
        return "ask"
    return "ask"


def normalize_terms(text: str) -> List[str]:
    terms = [
        term
        for term in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(term) > 2 and term not in STOPWORDS
    ]

    seen = set(terms)
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


def read_note(path: Path) -> Tuple[Dict[str, object], str]:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def score_note(question: str, metadata: Dict[str, object], body: str) -> int:
    haystack = f"{metadata.get('title', '')}\n{metadata.get('note_type', '')}\n{body}".lower()
    score = 0
    for term in normalize_terms(question):
        if term in haystack:
            score += 1
        title = str(metadata.get("title", "")).lower()
        if term in title:
            score += 2
    if metadata.get("note_type") == "synthesis":
        score += 1
    return score


def load_relation_edges(vault_root: Path) -> List[Dict[str, object]]:
    relation_index_path = vault_root / RELATION_INDEX_PATH
    if not relation_index_path.exists():
        return []

    try:
        payload = json.loads(relation_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    edges = payload.get("edges")
    if not isinstance(edges, list):
        return []
    return [edge for edge in edges if isinstance(edge, dict)]


def build_note_entry(vault_root: Path, note_path: Path, metadata: Dict[str, object], body: str, score: int) -> Dict[str, object]:
    resolved_root = vault_root.resolve()
    resolved_note = note_path.resolve()
    return {
        "path": resolved_note.relative_to(resolved_root).as_posix(),
        "title": metadata.get("title", note_path.stem),
        "note_type": metadata.get("note_type"),
        "primary_domain": metadata.get("primary_domain", ""),
        "source_refs": metadata.get("source_refs", []),
        "body": body,
        "score": score,
    }


def resolve_relation_candidate(vault_root: Path, candidate_path: str) -> Optional[Path]:
    raw_candidate = Path(candidate_path)
    if raw_candidate.is_absolute():
        return None

    candidate_file = (vault_root / raw_candidate).resolve()
    wiki_root = (vault_root / "30_Wiki").resolve()
    try:
        candidate_file.relative_to(wiki_root)
    except ValueError:
        return None

    if not candidate_file.exists() or not candidate_file.is_file():
        return None
    return candidate_file


def canonicalize_relation_path(vault_root: Path, note_path: str) -> str:
    candidate_file = resolve_relation_candidate(vault_root, note_path)
    if not candidate_file:
        return note_path
    return candidate_file.resolve().relative_to(vault_root.resolve()).as_posix()


def retrieve_lexical_notes(vault_root: Path, question: str) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    wiki_root = vault_root / "30_Wiki"
    if not wiki_root.exists():
        return [], []

    terms = normalize_terms(question)
    if not terms:
        return [], []

    synthesis: List[Tuple[int, Dict[str, object]]] = []
    small_notes: List[Tuple[int, Dict[str, object]]] = []

    for note_path in wiki_root.rglob("*.md"):
        metadata, body = read_note(note_path)
        note_type = metadata.get("note_type")
        if note_type not in SUPPORTED_NOTE_TYPES:
            continue
        score = score_note(question, metadata, body)
        if score <= 0:
            continue
        entry = build_note_entry(vault_root, note_path, metadata, body, score)
        if note_type == "synthesis":
            synthesis.append((score, entry))
        else:
            small_notes.append((score, entry))

    synthesis.sort(key=lambda item: item[0], reverse=True)
    small_notes.sort(key=lambda item: item[0], reverse=True)
    synthesis = [item for item in synthesis if item[0] >= 2]
    small_notes = [item for item in small_notes if item[0] >= 2]
    return [item[1] for item in synthesis[:5]], [item[1] for item in small_notes[:5]]


def expand_relation_notes(
    vault_root: Path,
    question: str,
    synthesis_notes: List[Dict[str, object]],
    small_notes: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    anchors = synthesis_notes + small_notes
    if not anchors:
        return synthesis_notes, small_notes

    edges = load_relation_edges(vault_root)
    if not edges:
        return synthesis_notes, small_notes

    anchor_scores = {str(note["path"]): int(note.get("score", 0)) for note in anchors}
    anchor_paths = set(anchor_scores)
    related_entries: Dict[str, Dict[str, object]] = {}

    for edge in edges:
        relation = str(edge.get("relation", ""))
        confidence = str(edge.get("confidence", ""))
        if relation not in SUPPORTED_RELATIONS:
            continue

        bonus = RELATION_CONFIDENCE_BONUS.get(confidence, 0)
        if bonus <= 0:
            continue

        source_note = str(edge.get("source_note", ""))
        target_note = str(edge.get("target_note", ""))
        if source_note in anchor_paths:
            candidate_path = target_note
            anchor_path = source_note
        elif target_note in anchor_paths:
            candidate_path = source_note
            anchor_path = target_note
        else:
            continue

        if not candidate_path:
            continue

        candidate_file = resolve_relation_candidate(vault_root, candidate_path)
        if not candidate_file:
            continue
        candidate_key = candidate_file.resolve().relative_to(vault_root.resolve()).as_posix()
        if candidate_key in anchor_paths:
            continue

        metadata, body = read_note(candidate_file)
        note_type = metadata.get("note_type")
        if note_type not in SUPPORTED_NOTE_TYPES:
            continue

        anchor_score = anchor_scores.get(anchor_path, 0)
        lexical_score = score_note(question, metadata, body)
        bounded_score = max(1, min(lexical_score + bonus, max(anchor_score - 1, 1)))
        relation_trace_item = {
            "source_note": source_note,
            "target_note": target_note,
            "relation": relation,
            "confidence": confidence,
        }

        existing = related_entries.get(candidate_key)
        if existing:
            traces = existing.setdefault("_relation_trace", [])
            if relation_trace_item not in traces:
                traces.append(relation_trace_item)
            if int(existing.get("score", 0)) >= bounded_score:
                continue
            existing["score"] = bounded_score
            existing["_relation_bonus"] = bonus
            existing["_anchor_path"] = anchor_path
            continue

        entry = build_note_entry(vault_root, candidate_file, metadata, body, bounded_score)
        entry["_relation_bonus"] = bonus
        entry["_anchor_path"] = anchor_path
        entry["_relation_trace"] = [relation_trace_item]
        related_entries[candidate_key] = entry

    if not related_entries:
        return synthesis_notes, small_notes

    ranked_related_entries = sorted(
        related_entries.values(),
        key=lambda entry: (int(entry.get("score", 0)), 1 if entry.get("note_type") == "synthesis" else 0),
        reverse=True,
    )

    expanded_synthesis = list(synthesis_notes)
    expanded_small = list(small_notes)
    for entry in ranked_related_entries:
        if entry.get("note_type") == "synthesis":
            expanded_synthesis.append(entry)
        else:
            expanded_small.append(entry)

    expanded_synthesis.sort(key=lambda note: int(note.get("score", 0)), reverse=True)
    expanded_small.sort(key=lambda note: int(note.get("score", 0)), reverse=True)
    return expanded_synthesis[:5], expanded_small[:5]


def retrieve_notes(vault_root: Path, question: str, mode: str) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    synthesis_notes, small_notes = retrieve_lexical_notes(vault_root, question)
    if mode != "ask":
        return synthesis_notes, small_notes
    return expand_relation_notes(vault_root, question, synthesis_notes, small_notes)


def local_answer(question: str, synthesis_notes: List[Dict[str, object]], small_notes: List[Dict[str, object]]) -> Tuple[str, List[str]]:
    if not synthesis_notes and not small_notes:
        return (
            INSUFFICIENT_GROUNDED_ANSWER,
            [INSUFFICIENT_GROUNDED_LIMIT],
        )

    strongest = max(
        synthesis_notes + small_notes,
        key=lambda note: (int(note.get("score", 0)), 1 if note.get("note_type") == "synthesis" else 0),
    )
    body = strongest["body"]
    definition_match = re.search(r"## Definition\s+(.+?)(?:\n##|\Z)", body, re.S)
    summary_match = re.search(r"## Source Summary\s+(.+?)(?:\n##|\Z)", body, re.S)
    if definition_match:
        core = " ".join(definition_match.group(1).split())
    elif summary_match:
        core = " ".join(summary_match.group(1).split())
    else:
        core = strongest["title"]

    note_titles = ", ".join(note["title"] for note in (synthesis_notes[:2] + small_notes[:2]))
    answer = f"{core} 目前可依據的筆記包括：{note_titles}。"
    return answer.strip(), []


def build_trace(notes: List[Dict[str, object]]) -> List[Dict[str, object]]:
    traces: List[Dict[str, object]] = []
    seen = set()
    for note in notes:
        for source_ref in note.get("source_refs", []):
            if source_ref in seen:
                continue
            seen.add(source_ref)
            traces.append({"source_ref": source_ref, "from_note": note["path"]})
    return traces


def build_relation_trace(vault_root: Path, notes: List[Dict[str, object]]) -> List[Dict[str, object]]:
    relation_trace: List[Dict[str, object]] = []
    seen = set()
    for note in notes:
        for trace in note.get("_relation_trace", []):
            if not isinstance(trace, dict):
                continue
            source_note = canonicalize_relation_path(vault_root, str(trace.get("source_note", "")))
            target_note = canonicalize_relation_path(vault_root, str(trace.get("target_note", "")))
            relation = str(trace.get("relation", ""))
            confidence = str(trace.get("confidence", ""))
            key = (source_note, target_note, relation, confidence)
            if key in seen:
                continue
            seen.add(key)
            relation_trace.append(
                {
                    "source_note": source_note,
                    "target_note": target_note,
                    "relation": relation,
                    "confidence": confidence,
                }
            )
    return relation_trace


def retrieve_reflections(vault_root: Path, grounding: List[Dict[str, object]]) -> List[Dict[str, object]]:
    reflections_root = vault_root / "50_Brainstorming" / "reflections"
    if not reflections_root.exists() or not grounding:
        return []

    linked_paths = {note["path"] for note in grounding}
    matches: List[Dict[str, object]] = []
    for reflection_path in reflections_root.rglob("*.md"):
        metadata, body = read_note(reflection_path)
        linked_note_ref = str(metadata.get("linked_note_ref", ""))
        if linked_note_ref not in linked_paths:
            continue
        matches.append(
            {
                "path": reflection_path.relative_to(vault_root).as_posix(),
                "title": metadata.get("title", reflection_path.stem),
                "linked_note_ref": linked_note_ref,
                "linked_note_title": metadata.get("linked_note_title", ""),
                "created_at": metadata.get("created_at", ""),
                "body": body,
            }
        )

    matches.sort(key=lambda item: (item["created_at"], item["path"]), reverse=True)
    return matches


def openai_answer(question: str, grounding: List[Dict[str, object]], model: str, api_key: str) -> str:
    context_blocks = []
    for note in grounding:
        context_blocks.append(
            f"Title: {note['title']}\nType: {note['note_type']}\nPath: {note['path']}\nContent:\n{note['body'].strip()}"
        )
    prompt = (
        "You are answering only from the user's private library. "
        "Use the provided grounded notes only. If the notes are insufficient, say so. "
        "Do not invent knowledge. Mark inference clearly.\n\n"
        f"Question:\n{question}\n\n"
        "Grounded notes:\n\n"
        + "\n\n---\n\n".join(context_blocks)
    )

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        input=prompt,
    )
    return response.output_text.strip()


def answer_question(
    vault_root: Path,
    question: str,
    requested_mode: str,
    settings: Dict[str, object],
    generate_answer: Optional[Callable[..., str]] = None,
) -> Dict[str, Any]:
    mode = infer_mode(question, requested_mode)
    synthesis_notes, small_notes = retrieve_notes(vault_root, question, mode)
    grounding = synthesis_notes + small_notes
    trace = build_trace(grounding)
    relation_trace = build_relation_trace(vault_root, grounding)
    reflections = retrieve_reflections(vault_root, grounding)

    if mode == "query":
        return {
            "mode": "query",
            "answer": "",
            "grounding": grounding,
            "trace": trace,
            "relation_trace": relation_trace,
            "reflections": reflections,
            "limits": [] if grounding else ["No matching notes found in the current library."],
            "answer_source": "local",
        }

    if not grounding:
        answer, limits = local_answer(question, synthesis_notes, small_notes)
        return {
            "mode": "ask",
            "answer": answer,
            "grounding": grounding,
            "trace": trace,
            "relation_trace": relation_trace,
            "reflections": reflections,
            "limits": limits,
            "answer_source": "local",
        }

    route = resolve_route_provider(settings, "ask")
    if route and route.get("provider") == "openai":
        generator = generate_answer or (lambda **kwargs: openai_answer(**kwargs))
        answer = generator(
            question=question,
            grounding=grounding,
            model=route["model"],
            api_key=route["api_key"],
        )
        return {
            "mode": "ask",
            "answer": answer,
            "grounding": grounding,
            "trace": trace,
            "relation_trace": relation_trace,
            "reflections": reflections,
            "limits": [],
            "answer_source": "model",
        }

    answer, limits = local_answer(question, synthesis_notes, small_notes)
    return {
        "mode": "ask",
        "answer": answer,
        "grounding": grounding,
        "trace": trace,
        "relation_trace": relation_trace,
        "reflections": reflections,
        "limits": limits,
        "answer_source": "local",
    }
