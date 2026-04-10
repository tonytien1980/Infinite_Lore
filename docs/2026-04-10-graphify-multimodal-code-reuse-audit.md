# Graphify Multimodal Code Reuse Audit

**Status:** Draft reference for the next multimodal lane
**Date:** 2026-04-10
**Source repo reviewed:** `https://github.com/safishamsi/graphify`
**Source snapshot reviewed:** `af3a3d2`

## 1. Purpose

This note records which parts of `Graphify` are worth reusing or adapting for the next `Infinite Lore` phase:

- multimodal intake
- `pptx` and image support
- selective ingest hardening

The user preference for this lane is explicit:

- use `Graphify` where it is genuinely reusable
- do not rebuild the whole thing from scratch if a useful engine part already exists

## 2. What Graphify Really Has Today

From the current repo state:

- `graphify/detect.py`
  - file classification
  - paper heuristics
  - `pdf`
  - `docx`
  - `xlsx`
  - image extension support
- `graphify/ingest.py`
  - URL type detection
  - safe binary fetch for `pdf` and image URLs
  - webpage / tweet / arXiv ingest patterns
- `README.md`
  - claims multimodal support for code, docs, papers, and images
- skill files
  - describe semantic extraction over docs, papers, and images

Important reality check:

- `Graphify` does **not** currently ship a real `pptx` adapter
- the strongest image understanding logic is described at workflow / skill level, not as a standalone reusable Python multimodal module

## 3. Best Direct Reuse Candidates

### 3.1 `graphify/detect.py`

This is the strongest direct reuse target.

Useful parts:

- `FileType`
- extension buckets
- paper-vs-document heuristics
- office conversion helpers:
  - `extract_pdf_text()`
  - `docx_to_markdown()`
  - `xlsx_to_markdown()`
  - `convert_office_file()`

Why it matters:

- `Infinite Lore` also needs a first routing layer before adapter execution
- the separation between classify first and extract second is strong and reusable

### 3.2 `graphify/ingest.py`

This is the strongest direct reuse target for later remote multimodal intake.

Useful parts:

- `_detect_url_type()`
- `_download_binary()`
- `ingest()` structure
- URL validation via `graphify/security.py`

Why it matters:

- image-heavy sources and PDF sources should reuse existing binary fetch discipline
- this is more valuable than inventing a fresh downloader

## 4. Strong Reference Patterns, Not Direct Drop-In Code

### 4.1 Stage separation

Best pattern to mirror:

- detect
- extract
- validate
- save / bundle-write

This is a better reuse target than any single file transplant because it fits `Infinite Lore` directly.

### 4.2 Image understanding posture

What is useful:

- treat images as semantic input, not only OCR text
- support screenshots, diagrams, and image-heavy notes
- keep uncertainty visible

What is not directly reusable:

- the actual multimodal semantic extraction is not contained in one clean Python library module we can vendor wholesale

## 5. What Graphify Does Not Solve For Us

### 5.1 No real `pptx` adapter

This is the biggest gap.

Current reviewed files show:

- office support means `docx` and `xlsx`
- not `pptx`

So for `Infinite Lore`:

- `pptx` architecture can borrow the same detect / adapter discipline
- but the adapter itself still needs to be built

### 5.2 No product-compatible bundle writer

`Graphify` writes:

- extraction JSON
- graph outputs
- report outputs

It does not write:

- `content.md`
- `metadata.md`
- `assets/`

in the exact raw bundle contract that `Infinite Lore` already uses.

So the right reuse boundary is:

- borrow detection and ingest helpers
- keep our own bundle writer

## 6. Recommended Reuse Order

The recommended reuse order for the multimodal lane is:

1. adapt file classification and conversion helper patterns from `graphify/detect.py`
2. adapt binary ingest safety from `graphify/ingest.py`
3. mirror `detect -> extract -> validate -> bundle-write`
4. keep semantic image understanding narrow and explainable
5. build a real `pptx` adapter on top of that structure

## 7. What Not To Reuse

Do not adopt for this phase:

- graph UI
- graph export
- graph server / MCP layer
- graph-first workflow
- cluster / analyze / report stack

Those do not help `Infinite Lore` ingest a `pptx` or screenshot into the existing library flow.

## 8. Bottom Line

The right interpretation of “reuse Graphify” for the multimodal lane is:

- reuse its real detection and ingest discipline
- reuse its file-type thinking
- reuse its safety posture
- reuse its stage separation

But do not fake reuse where the code does not actually exist.

For `Infinite Lore`:

- image support can borrow more directly
- `pptx` support still needs a real adapter implementation

That is still selective reuse, not a full reinvention.

