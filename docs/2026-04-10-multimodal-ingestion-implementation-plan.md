# Multimodal Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real `pptx` and image import support to the existing raw bundle pipeline without creating a second ingest architecture.

**Architecture:** Introduce a shared multimodal detection / adapter layer, then plug `pptx` and image handling into the current raw bundle writer so downstream compile and Ask continue unchanged. Reuse real `Graphify` engine parts where they exist, especially detection and binary-ingest discipline, but keep the `Infinite Lore` bundle contract and workflow intact.

**Tech Stack:** Python 3.9, existing `tools/import_bundle.py`, bundle-based raw intake, `python-pptx` or equivalent `pptx` parser, existing metadata contract, unittest

---

## File Structure

- Modify: `tools/import_bundle.py`
  - keep the top-level import entrypoint and existing bundle writer
- Create: `tools/multimodal_detect.py`
  - shared file classification and multimodal routing helpers adapted from `Graphify detect.py`
- Create: `tools/pptx_adapter.py`
  - extract slide text, slide notes when available, and embedded images
- Create: `tools/image_adapter.py`
  - extract image text / summary into the common intermediate contract
- Test: `tests/test_import_bundle.py`
  - end-to-end raw bundle coverage for `pptx` and image imports
- Test: `tests/test_multimodal_detect.py`
  - routing and file-classification behavior

This structure keeps the import entrypoint stable while moving multimodal-specific logic into smaller files.

## Task 1: Add Multimodal Detection Helpers

**Files:**
- Create: `tools/multimodal_detect.py`
- Test: `tests/test_multimodal_detect.py`

- [ ] **Step 1: Write failing detection tests**

Cover:

- `pptx` classifies as multimodal office input
- `.png/.jpg/.jpeg/.webp` classify as image input
- unsupported files still return `None`

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_multimodal_detect -v
```

Expected:

- FAIL because the detection helper module does not exist yet

- [ ] **Step 3: Implement the shared detection helper**

Use `Graphify` as the reference for:

- extension buckets
- classify-first design
- explicit file-type enums

Do not copy over graph-specific concerns.

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
python3 -m unittest tests.test_multimodal_detect -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add tools/multimodal_detect.py tests/test_multimodal_detect.py
git commit -m "feat: add multimodal detection helpers"
```

## Task 2: Add Failing End-To-End PPTX And Image Import Tests

**Files:**
- Modify: `tests/test_import_bundle.py`

- [ ] **Step 1: Add failing `pptx` and image raw bundle tests**

Cover:

- `pptx` import no longer raises the reserved-phase error
- image import no longer raises the reserved-phase error
- both create:
  - preserved `source.*`
  - `content.md`
  - `metadata.md`

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_import_bundle -v
```

Expected:

- FAIL on the new `pptx` and image tests because these formats are still reserved

- [ ] **Step 3: Commit the red test coverage**

```bash
git add tests/test_import_bundle.py
git commit -m "test: add multimodal import coverage"
```

## Task 3: Implement The PPTX Adapter

**Files:**
- Create: `tools/pptx_adapter.py`
- Modify: `tools/import_bundle.py`
- Test: `tests/test_import_bundle.py`

- [ ] **Step 1: Implement a shared `pptx` extraction result contract**

Return:

- title
- source filename / bytes
- normalized slide Markdown
- asset paths
- warnings
- extraction confidence

- [ ] **Step 2: Extract slide text and embedded images**

The first version should favor:

- slide titles
- bullet text
- embedded image extraction into `assets/`

It does not need perfect visual deck reconstruction.

- [ ] **Step 3: Wire the adapter into `import_bundle.py`**

Replace the reserved `pptx` error with the real adapter path while preserving the current bundle writer contract.

- [ ] **Step 4: Re-run the import tests**

Run:

```bash
python3 -m unittest tests.test_import_bundle -v
```

Expected:

- `pptx` tests PASS
- existing import tests remain green

- [ ] **Step 5: Commit**

```bash
git add tools/pptx_adapter.py tools/import_bundle.py tests/test_import_bundle.py
git commit -m "feat: add pptx raw import support"
```

## Task 4: Implement The Image Adapter

**Files:**
- Create: `tools/image_adapter.py`
- Modify: `tools/import_bundle.py`
- Test: `tests/test_import_bundle.py`

- [ ] **Step 1: Implement the image extraction result contract**

Return:

- title
- source filename / bytes
- normalized Markdown summary
- warnings
- confidence
- optional support assets

- [ ] **Step 2: Add the first usable image understanding path**

The first version should support:

- extracted visible text when possible
- a concise structural summary
- review warnings when confidence is weak

This must still produce a usable bundle even when extraction quality is partial.

- [ ] **Step 3: Wire the image adapter into `import_bundle.py`**

Replace the reserved image error path with the real adapter path.

- [ ] **Step 4: Re-run the import tests**

Run:

```bash
python3 -m unittest tests.test_import_bundle -v
```

Expected:

- image tests PASS
- existing import tests remain green

- [ ] **Step 5: Commit**

```bash
git add tools/image_adapter.py tools/import_bundle.py tests/test_import_bundle.py
git commit -m "feat: add image raw import support"
```

## Task 5: Reuse Hardening From Graphify Where It Actually Helps

**Files:**
- Modify: `tools/multimodal_detect.py`
- Modify: `tools/import_bundle.py`
- Modify: tests as needed

- [ ] **Step 1: Add failing hardening tests**

Cover:

- malformed or unsupported multimodal files fail clearly
- file classification does not silently drift to the wrong adapter
- metadata warnings and review flags remain populated when extraction is partial

- [ ] **Step 2: Adapt the useful Graphify hardening patterns**

Focus on:

- explicit file-type classification
- conservative confidence defaults
- bounded warning behavior

Do not import graph-specific output semantics.

- [ ] **Step 3: Re-run targeted suites**

Run:

```bash
python3 -m unittest tests.test_multimodal_detect tests.test_import_bundle -v
```

Expected:

- PASS

- [ ] **Step 4: Commit**

```bash
git add tools/multimodal_detect.py tools/import_bundle.py tests/test_multimodal_detect.py tests/test_import_bundle.py
git commit -m "fix: harden multimodal import routing"
```

## Task 6: Docs And Full Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-10-multimodal-ingestion-spec.md` only if implementation changes behavior

- [ ] **Step 1: Update workflow docs**

Document:

- `pptx` import support
- image import support
- multimodal bundles still feed the same compile / Ask flow

- [ ] **Step 2: Run the full verification suite**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_query_ask tests.test_reflection_feedback tests.test_automation_scan tests.test_relation_index tests.test_health_check tests.test_multimodal_detect -v
python3 tools/health_check.py .
```

Expected:

- all tests PASS
- health check prints `Vault health check passed`

- [ ] **Step 3: Commit**

```bash
git add 00_System/Workflow Guide.md docs/2026-04-08-execution-roadmap.md docs/2026-04-10-multimodal-ingestion-spec.md docs/2026-04-10-multimodal-ingestion-implementation-plan.md docs/2026-04-10-graphify-multimodal-code-reuse-audit.md
git commit -m "docs: sync multimodal ingestion rollout"
```

