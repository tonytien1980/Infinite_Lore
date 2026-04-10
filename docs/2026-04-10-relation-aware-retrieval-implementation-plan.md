# Relation-Aware Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first relation layer that improves `Ask` retrieval through explicit, confidence-labeled note relations without turning the product into a graph-first tool.

**Architecture:** Add a generated relation artifact beside the vault system notes, refresh it from compiled wiki notes, and use it to expand and re-rank Ask candidates only after lexical anchors are found. Keep the first version narrow: `derived-from` and `shares-source` edges only, full rebuild after compile, and a small relation-trace addition to the Ask surface.

**Tech Stack:** Python 3.9 standard library, existing compile and Ask services, JSON relation artifact, unittest, existing Workbench frontend

---

## File Structure

### New files

- `tools/relation_index.py`
  - Purpose: build, serialize, and save the relation artifact from compiled wiki notes.
- `tests/test_relation_index.py`
  - Purpose: verify relation extraction, confidence labels, exclusion rules, and artifact shape.

### Modified files

- `tools/wiki_compile.py`
  - Refresh the relation artifact after compile changes the wiki.
- `workbench/ask_service.py`
  - Expand Ask retrieval through the relation artifact and return relation trace data.
- `workbench/static/index.html`
  - Add a compact relation-trace section inside Ask results.
- `workbench/static/app.js`
  - Render relation trace without adding a new page.
- `tests/test_wiki_compile.py`
  - Verify compile refreshes the relation artifact.
- `tests/test_query_ask.py`
  - Verify relation-aware retrieval improves Ask while preserving abstention boundaries.
- `tests/test_workbench_api.py`
  - Verify Ask responses include the relation-trace field through the API.
- `00_System/Workflow Guide.md`
  - Add the relation-aware Ask workflow after implementation.
- `docs/2026-04-08-execution-roadmap.md`
  - Mark the Phase 8 planning lane appropriately after implementation.

### Generated artifact

- `00_System/relation-index.json`
  - Generated output only.
  - Not hand-edited.

### Explicit boundary

- No `pptx`, OCR, or image-extraction implementation in this plan.
- Those belong to a later multimodal phase after relation-aware retrieval is proven useful.

---

### Task 1: Add Failing Relation Artifact Tests

**Files:**
- Create: `tests/test_relation_index.py`

- [ ] **Step 1: Write failing extraction tests**

Add tests that cover:

```python
import json
import tempfile
import unittest
from pathlib import Path

from tools.relation_index import build_relation_index


class RelationIndexTests(unittest.TestCase):
    def test_extracts_derived_from_edge_from_compiled_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "30_Wiki" / "ai-application"
            wiki.mkdir(parents=True)
            (wiki / "source--synthesis.md").write_text(
                "---\n"
                "title: Source Synthesis\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/a\"]\n"
                "---\n\n# Synthesis\n",
                encoding="utf-8",
            )
            (wiki / "source--concept--foo.md").write_text(
                "---\n"
                "title: Foo\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/a\"]\n"
                "compiled_from: 30_Wiki/ai-application/source--synthesis.md\n"
                "---\n\n# Foo\n",
                encoding="utf-8",
            )

            artifact = build_relation_index(root)

            self.assertTrue(
                any(
                    edge["relation"] == "derived-from"
                    and edge["confidence"] == "EXTRACTED"
                    for edge in artifact["edges"]
                )
            )

    def test_extracts_shares_source_edge_from_overlapping_source_refs(self) -> None:
        ...

    def test_excludes_reflection_and_correction_notes(self) -> None:
        ...
```

- [ ] **Step 2: Run the test file to verify it fails**

Run:

```bash
python3 -m unittest tests.test_relation_index -v
```

Expected:

- FAIL because `tools.relation_index` does not exist yet

- [ ] **Step 3: Commit the failing-test checkpoint**

```bash
git add tests/test_relation_index.py
git commit -m "test: add relation artifact extraction coverage"
```

---

### Task 2: Build The Relation Artifact Module

**Files:**
- Create: `tools/relation_index.py`
- Test: `tests/test_relation_index.py`

- [ ] **Step 1: Implement the relation-index builder**

Create `tools/relation_index.py` with functions like:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from tools.wiki_compile import parse_frontmatter


RELATION_INDEX_PATH = Path("00_System/relation-index.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_wiki_note(path: Path) -> Tuple[Dict[str, object], str]:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def build_relation_index(root: Path) -> Dict[str, object]:
    ...


def save_relation_index(root: Path) -> Dict[str, object]:
    artifact = build_relation_index(root)
    target = root / RELATION_INDEX_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return artifact
```

- [ ] **Step 2: Implement the first relation rules**

Implement only:

- `derived-from`
  - confidence `EXTRACTED`
  - evidence from `compiled_from`
- `shares-source`
  - confidence `INFERRED`
  - evidence from overlapping `source_refs` or matching `raw_bundle_ref`

- [ ] **Step 3: Keep exclusions explicit**

Exclude:

- `reflection-entry`
- `correction-proposal`
- non-`30_Wiki` notes

- [ ] **Step 4: Re-run relation-index tests**

Run:

```bash
python3 -m unittest tests.test_relation_index -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add tools/relation_index.py tests/test_relation_index.py
git commit -m "feat: add relation artifact builder"
```

---

### Task 3: Refresh The Relation Artifact After Compile

**Files:**
- Modify: `tools/wiki_compile.py`
- Modify: `tests/test_wiki_compile.py`

- [ ] **Step 1: Add a failing compile integration test**

Add a test such as:

```python
    def test_compile_refreshes_relation_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = ...

            compile_bundle(root, bundle)

            relation_index = root / "00_System/relation-index.json"
            self.assertTrue(relation_index.exists())
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_wiki_compile.WikiCompileTests.test_compile_refreshes_relation_index -v
```

Expected:

- FAIL because compile does not refresh the artifact yet

- [ ] **Step 3: Call `save_relation_index(root)` at the end of compile**

Keep the first version simple:

- compile succeeds
- relation artifact refresh runs after wiki notes are written

- [ ] **Step 4: Re-run the targeted and full compile tests**

Run:

```bash
python3 -m unittest tests.test_wiki_compile -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add tools/wiki_compile.py tests/test_wiki_compile.py
git commit -m "feat: refresh relation artifact after compile"
```

---

### Task 4: Add Relation-Aware Retrieval To Ask

**Files:**
- Modify: `workbench/ask_service.py`
- Modify: `tests/test_query_ask.py`

- [ ] **Step 1: Add failing Ask retrieval tests**

Add tests that prove:

```python
    def test_relation_aware_retrieval_expands_from_lexical_anchor(self) -> None:
        ...

    def test_relation_aware_retrieval_does_not_override_insufficient_evidence_without_anchor(self) -> None:
        ...

    def test_relation_aware_retrieval_ignores_reflection_entries(self) -> None:
        ...
```

- [ ] **Step 2: Run the targeted Ask tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_query_ask -v
```

Expected:

- FAIL on the new relation-aware retrieval cases

- [ ] **Step 3: Implement bounded relation expansion**

Add logic in `workbench/ask_service.py` to:

- load `00_System/relation-index.json`
- keep the existing lexical retrieval
- choose a small anchored note set first
- expand through:
  - `derived-from`
  - `shares-source`
- ignore `AMBIGUOUS` edges for answer expansion in this version
- add a confidence-aware bonus during ranking

- [ ] **Step 4: Keep abstention boundaries intact**

Make sure:

- relations do not create an answer when lexical anchors are missing
- weak relations do not silently override the insufficient-evidence path

- [ ] **Step 5: Re-run the Ask test file**

Run:

```bash
python3 -m unittest tests.test_query_ask -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add workbench/ask_service.py tests/test_query_ask.py
git commit -m "feat: add relation-aware ask retrieval"
```

---

### Task 5: Surface Relation Trace In Ask

**Files:**
- Modify: `workbench/ask_service.py`
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add a failing API/UI contract test**

Add a test like:

```python
    def test_ask_endpoint_returns_relation_trace(self) -> None:
        ...
        self.assertIn("relation_trace", payload)
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_workbench_api.WorkbenchApiTests.test_ask_endpoint_returns_relation_trace -v
```

Expected:

- FAIL because the response does not include relation trace yet

- [ ] **Step 3: Add a small relation-trace section to Ask results**

Keep the surface minimal:

- no new page
- no graph canvas
- one compact list showing:
  - source note
  - target note
  - relation type
  - confidence

- [ ] **Step 4: Re-run API tests**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add workbench/ask_service.py workbench/static/index.html workbench/static/app.js tests/test_workbench_api.py
git commit -m "feat: expose ask relation trace"
```

---

### Task 6: Docs And Full Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-10-relation-aware-retrieval-spec.md` only if implementation changes behavior

- [ ] **Step 1: Update the workflow guide**

Add a short section describing:

- Ask now uses relation-aware expansion
- relation trace appears in Ask results
- multimodal remains a later phase

- [ ] **Step 2: Update the roadmap**

Update the roadmap so:

- Phase 8 is represented as the current delivered lane after implementation
- multimodal remains the next adjacent future lane

- [ ] **Step 3: Run the full verification suite**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_query_ask tests.test_reflection_feedback tests.test_automation_scan tests.test_relation_index tests.test_health_check -v
python3 tools/health_check.py .
```

Expected:

- all tests PASS
- health check prints `Vault health check passed`

- [ ] **Step 4: Commit**

```bash
git add 00_System/Workflow Guide.md docs/2026-04-08-execution-roadmap.md docs/2026-04-10-relation-aware-retrieval-spec.md docs/2026-04-10-relation-aware-retrieval-implementation-plan.md
git commit -m "docs: sync relation-aware retrieval rollout"
```

- [ ] **Step 5: Final sync**

```bash
git push origin codex/foundation-bootstrap
```

Expected:

- branch is clean
- local and remote are aligned

---

## Self-Review

- Spec coverage:
  - relation artifact, confidence labels, Ask expansion, relation trace, compile refresh, and multimodal boundary are all represented in the task list.
- Placeholder scan:
  - no placeholder markers or deferred-implementation notes remain in the plan tasks.
- Boundary check:
  - multimodal is documented as a future lane, not mixed into this implementation plan.
