from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from tools.wiki_compile import parse_frontmatter


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
    return [
        term
        for term in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(term) > 2 and term not in STOPWORDS
    ]


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


def retrieve_notes(vault_root: Path, question: str) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
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
        if note_type not in {"synthesis", "concept", "framework", "question", "reference"}:
            continue
        score = score_note(question, metadata, body)
        if score <= 0:
            continue
        entry = {
            "path": note_path.relative_to(vault_root).as_posix(),
            "title": metadata.get("title", note_path.stem),
            "note_type": note_type,
            "primary_domain": metadata.get("primary_domain", ""),
            "source_refs": metadata.get("source_refs", []),
            "body": body,
        }
        if note_type == "synthesis":
            synthesis.append((score, entry))
        else:
            small_notes.append((score, entry))

    synthesis.sort(key=lambda item: item[0], reverse=True)
    small_notes.sort(key=lambda item: item[0], reverse=True)
    synthesis = [item for item in synthesis if item[0] >= 2]
    small_notes = [item for item in small_notes if item[0] >= 2]
    return [item[1] for item in synthesis[:5]], [item[1] for item in small_notes[:5]]


def local_answer(question: str, synthesis_notes: List[Dict[str, object]], small_notes: List[Dict[str, object]]) -> Tuple[str, List[str]]:
    if not synthesis_notes and not small_notes:
        return (
            "The library does not currently contain enough grounded knowledge to answer this confidently.",
            ["Insufficient evidence in the current wiki."],
        )

    strongest = small_notes[0] if small_notes else synthesis_notes[0]
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
    answer = f"{core} The current grounded answer is based on: {note_titles}."
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


def resolve_route_model(settings: Dict[str, object], route_name: str) -> Optional[Dict[str, str]]:
    role = settings.get("routes", {}).get(route_name)
    if not role or role == "no_model":
        return None

    for provider in settings.get("providers", []):
        provider_name = provider.get("provider")
        api_key = provider.get("api_key")
        if provider_name != "openai" or not api_key:
            continue
        for model in provider.get("models", []):
            if model.get("role") == role and model.get("id"):
                return {
                    "provider": provider_name,
                    "model": model["id"],
                    "api_key": api_key,
                }
    return None


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
    synthesis_notes, small_notes = retrieve_notes(vault_root, question)
    grounding = synthesis_notes + small_notes
    trace = build_trace(grounding)

    if mode == "query":
        return {
            "mode": "query",
            "answer": "",
            "grounding": grounding,
            "trace": trace,
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
            "limits": limits,
            "answer_source": "local",
        }

    route = resolve_route_model(settings, "ask")
    if route:
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
            "limits": [],
            "answer_source": "model",
        }

    answer, limits = local_answer(question, synthesis_notes, small_notes)
    return {
        "mode": "ask",
        "answer": answer,
        "grounding": grounding,
        "trace": trace,
        "limits": limits,
        "answer_source": "local",
    }
