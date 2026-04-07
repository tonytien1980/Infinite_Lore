# Wiki Compile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first lightweight `raw bundle -> wiki` compiler, including source-grounded synthesis notes, conservative small-note extraction and merge, lineage write-back, domain index updates, and auto-compile from the import CLI.

**Architecture:** The implementation adds a dedicated compile module that reads raw bundle `content.md` and `metadata.md`, writes source-specific synthesis notes plus a few reusable small notes, and updates bundle metadata and domain index notes. The existing importer remains the bundle creator, but its CLI will trigger compile automatically after successful import so the user only performs one step.

**Tech Stack:** Python 3.9 standard library, `unittest`, existing raw bundle contract, Markdown, YAML-like frontmatter

---

## File Structure

### Files to create

- `docs/2026-04-08-wiki-compile-implementation-plan.md`
- `tools/wiki_compile.py`
- `tests/test_wiki_compile.py`

### Files to modify

- `00_System/Workflow Guide.md`
- `docs/2026-04-07-wiki-compile-spec.md`
- `tools/import_bundle.py`

## Task 1: Update Workflow Guidance For One-Step Import And Compile

**Files:**

- Modify: `00_System/Workflow Guide.md`

- [ ] **Step 1: Replace the raw import section with the one-step ingest workflow**

Update the raw import section in `00_System/Workflow Guide.md` to:

```md
## Raw Import

Use the importer to normalize new source material into raw bundles and immediately compile it into wiki notes:

```bash
python3 tools/import_bundle.py --source <path-or-url> --domain <primary-domain>
```

This creates a raw bundle in `20_Raw/inbox/`, then automatically produces source-grounded wiki notes in `30_Wiki/<domain>/`.
```

- [ ] **Step 2: Verify the workflow guide reflects the one-step flow**

Run:

```bash
sed -n '1,220p' '00_System/Workflow Guide.md'
```

Expected:

- the raw import section states that import and compile happen in one top-level command

## Task 2: Write Failing Wiki Compile Tests

**Files:**

- Create: `tests/test_wiki_compile.py`

- [ ] **Step 1: Write tests for synthesis creation, small-note merge, bundle metadata update, and domain index update**

Create `tests/test_wiki_compile.py` with:

```python
import tempfile
import unittest
from pathlib import Path

from tools.import_bundle import import_source
from tools.wiki_compile import compile_bundle


class WikiCompileTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_compile_creates_synthesis_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text(
                "---\n"
                "title: AI Application\n"
                "layer: domain-index\n"
                "note_type: domain-index\n"
                "primary_domain: ai-application\n"
                "related_domains: []\n"
                "privacy: private\n"
                "status: active\n"
                "created_at: 2026-04-08\n"
                "updated_at: 2026-04-08\n"
                "source_refs: []\n"
                "---\n\n"
                "# AI Application\n",
                encoding="utf-8",
            )
            source = root / "note.txt"
            source.write_text(
                "# Knowledge Compilation\n\nKnowledge compilation helps transform raw material into reusable notes.\n\nWhat makes a source-grounded synthesis trustworthy?\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "ai-application")

            result = compile_bundle(root, bundle)

            synthesis_path = root / result["synthesis_path"]
            self.assertTrue(synthesis_path.exists())
            synthesis = self.read(synthesis_path)
            self.assertIn("## Source Summary", synthesis)
            self.assertIn("## Key Points", synthesis)
            self.assertIn("## Source Lineage", synthesis)

    def test_compile_extracts_and_writes_question_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/management").mkdir(parents=True)
            (root / "10_Domains/management").mkdir(parents=True)
            (root / "10_Domains/management/index.md").write_text("# Management\n", encoding="utf-8")
            source = root / "question.txt"
            source.write_text(
                "# Team Decisions\n\nHow should a team make faster decisions?\n\nA good decision process should be reusable.\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "management")

            result = compile_bundle(root, bundle)

            self.assertTrue(result["small_note_paths"])
            note_text = self.read(root / result["small_note_paths"][0])
            self.assertIn("note_type: question", note_text)
            self.assertIn("How should a team make faster decisions?", note_text)

    def test_compile_merges_matching_small_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")

            existing = root / "30_Wiki/ai-application/old-source--concept--knowledge-compilation.md"
            existing.write_text(
                "---\n"
                "id: old-source--concept--knowledge-compilation\n"
                "title: Knowledge Compilation\n"
                "layer: wiki\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "related_domains: []\n"
                "privacy: private\n"
                "status: active\n"
                "created_at: 2026-04-08\n"
                "updated_at: 2026-04-08\n"
                "source_refs: [\"raw/old\"]\n"
                "confidence: medium\n"
                "last_compiled_at: 2026-04-08T00:00:00Z\n"
                "last_reviewed_at:\n"
                "raw_bundle_ref:\n"
                "compiled_from:\n"
                "---\n\n"
                "# Knowledge Compilation\n\n"
                "## Definition\nExisting definition.\n\n"
                "## Supporting Evidence\n- Existing evidence.\n\n"
                "## Source Lineage\n- raw/old\n",
                encoding="utf-8",
            )

            source = root / "new.txt"
            source.write_text(
                "# Knowledge Compilation\n\nKnowledge compilation helps turn source material into reusable knowledge.\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "ai-application")

            result = compile_bundle(root, bundle)

            self.assertEqual(len(result["small_note_paths"]), 1)
            self.assertEqual(result["small_note_paths"][0], "30_Wiki/ai-application/old-source--concept--knowledge-compilation.md")
            merged_text = self.read(existing)
            self.assertIn("Knowledge compilation helps turn source material into reusable knowledge.", merged_text)

    def test_compile_updates_bundle_metadata_and_domain_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/business-strategy").mkdir(parents=True)
            (root / "10_Domains/business-strategy").mkdir(parents=True)
            index_path = root / "10_Domains/business-strategy/index.md"
            index_path.write_text("# Business Strategy\n", encoding="utf-8")
            source = root / "strategy.txt"
            source.write_text(
                "# Repeatable Strategy\n\nA repeatable strategy helps teams focus.\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "business-strategy")

            result = compile_bundle(root, bundle)

            metadata_text = self.read(bundle / "metadata.md")
            index_text = self.read(index_path)
            self.assertIn("compiled_at:", metadata_text)
            self.assertIn("compiled_note_refs:", metadata_text)
            self.assertIn(result["synthesis_path"], metadata_text)
            self.assertIn("## Recently Compiled", index_text)
            self.assertIn("repeatable-strategy--synthesis", index_text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_wiki_compile -v
```

Expected:

- failure because `tools.wiki_compile` does not exist yet

## Task 3: Implement The Wiki Compiler

**Files:**

- Create: `tools/wiki_compile.py`

- [ ] **Step 1: Create the compile module with bundle parsing, synthesis generation, small-note extraction, merge-or-create logic, lineage updates, and domain index update**

Create `tools/wiki_compile.py` with code that provides:

- `compile_bundle(root: Path, bundle_path: Path) -> dict`
- frontmatter parsing and writing helpers
- `build_synthesis_note(...)`
- `extract_small_note_candidates(...)`
- `merge_or_create_small_note(...)`
- `update_bundle_metadata(...)`
- `update_domain_index(...)`

The implementation must support:

- one synthesis note per bundle
- `0-3` small notes
- question extraction from question-mark lines
- concept extraction from H1 or H2 headings when suitable
- merge-first behavior using:
  - same `note_type`
  - same `primary_domain`
  - matching `--<note-type>--<concept-slug>.md` suffix

- [ ] **Step 2: Run the tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_wiki_compile -v
```

Expected:

- all 4 tests pass

## Task 4: Wire Auto-Compile Into The Import CLI

**Files:**

- Modify: `tools/import_bundle.py`

- [ ] **Step 1: Add automatic compile behavior to the CLI path**

Update `tools/import_bundle.py` so that:

- `import_source(...)` still only creates the bundle
- `main()` imports `compile_bundle` from `tools.wiki_compile`
- after successful import, `main()` runs `compile_bundle(...)`
- add a `--skip-compile` flag for debugging

- [ ] **Step 2: Verify the importer still works as a one-step command**

Run:

```bash
mkdir -p tmp/manual-compile
printf '# Library Systems\n\nA library system organizes knowledge into reusable access points.\n' > tmp/manual-compile/sample.txt
python3 tools/import_bundle.py --source tmp/manual-compile/sample.txt --domain ai-application --root .
```

Expected:

- command prints the created bundle path
- a synthesis note appears in `30_Wiki/ai-application/`

## Task 5: Full Verification

**Files:**

- Verify all files changed in this plan

- [ ] **Step 1: Run all current tests**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_health_check -v
```

Expected:

- all tests pass

- [ ] **Step 2: Run the vault health check**

Run:

```bash
python3 tools/health_check.py .
```

Expected:

- `Vault health check passed`

- [ ] **Step 3: Verify the git working tree only contains the wiki compile scope**

Run:

```bash
git status --short
```

Expected:

- changed files match the compiler implementation scope
