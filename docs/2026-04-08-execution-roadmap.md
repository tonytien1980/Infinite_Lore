# Infinite Lore Execution Roadmap

**Status:** Active execution reference  
**Date:** 2026-04-08  
**Purpose:** This document is the working sequence reference for building `Infinite Lore` without losing direction during long conversations or multi-step execution.

## 1. How To Use This Document

Before starting a new implementation phase, check this file first.

This document exists to answer:

- what has already been finished
- what order the remaining work should happen in
- what must not be skipped or reversed
- what the next most important phase is

This is not a replacement for the system specs. It is the sequencing and execution reference that sits beside the specs.

## 2. Core Product Direction

`Infinite Lore` is an Obsidian-native, AI-maintained personal LLM Wiki and context system.

The system is designed for:

- one primary user
- clean source-grounded knowledge
- fast ingest and lightweight compile
- later refinement through actual use and feedback

The system is not designed to be:

- a heavy evaluator factory
- a multi-user knowledge platform
- a custom frontend replacement for Obsidian

## 3. Non-Negotiable Operating Principles

- `raw` remains preserved and is not overwritten
- `wiki` is living and updatable
- `source-grounded knowledge` must stay separate from `personal interpretation`
- import should be fast
- compile should be lightweight
- deeper refinement should happen later during use, not during every ingest run
- Obsidian is the knowledge workspace
- external tooling handles import, compile, and health-check work
- documentation and implementation must stay aligned
- relevant skills must be used when they exist
- verified milestones must be pushed so local and GitHub stay in sync
- repeated workflow expectations should be written into repo docs, not left in chat only

## 4. What Is Already Done

### 4.1 Foundation

Completed:

- vault skeleton
- domain entry notes
- system notes
- note templates
- basic health checker

Reference files:

- `docs/2026-04-07-infinite-lore-system-spec.md`
- `docs/2026-04-07-infinite-lore-foundation-implementation-plan.md`

Reference commits:

- `2006326` `chore: bootstrap infinite lore foundation`

### 4.2 Multi-format import pipeline

Completed:

- bundle-based raw import model
- support for `txt`, `md`, `html`, file-based article import, `docx`, and `pdf`
- importer metadata contract
- one command entrypoint for import

Reference files:

- `docs/2026-04-07-multi-format-import-pipeline-spec.md`
- `docs/2026-04-07-multi-format-import-pipeline-implementation-plan.md`

Reference commits:

- `d909ecc` `docs: add multi-format import pipeline spec`
- `833e1f9` `feat: add multi-format raw importer`

### 4.3 Wiki compile pipeline

Completed:

- source-grounded synthesis generation
- conservative small-note extraction
- merge-first update behavior for small notes
- bundle metadata compile tracking
- domain index recent compile update
- one-step import plus auto-compile flow

Reference files:

- `docs/2026-04-07-wiki-compile-spec.md`
- `docs/2026-04-08-wiki-compile-implementation-plan.md`

Reference commits:

- `db101a5` `docs: add wiki compile spec`
- `501364a` `docs: refine wiki compile workflow`
- `a5e9b80` `feat: add wiki compile pipeline`

### 4.4 External Workbench UI

Completed:

- local Workbench backend
- local Workbench frontend
- browser-based operational surface for non-Obsidian tasks
- local settings and model routing UI
- import and compile access through UI
- system and health visibility through UI

Reference files:

- `docs/2026-04-08-workbench-ui-spec.md`
- `docs/2026-04-08-workbench-ui-implementation-plan.md`

Reference commits:

- `8f2d6e0` `docs: add workbench ui spec`
- `f012275` `feat: add workbench ui`

### 4.5 Query / Ask Layer

Completed:

- single Ask input with auto routing between Ask and Query
- local retrieval over compiled wiki notes
- grounded Ask answers with visible note grounding
- visible raw lineage trace
- strict abstention behavior when evidence is insufficient
- OpenAI-backed answer synthesis when an OpenAI route is configured

Reference files:

- `docs/2026-04-08-query-ask-spec.md`
- `docs/2026-04-08-query-ask-implementation-plan.md`

### 4.6 Reflection / Feedback Layer

Completed:

- same-page feedback loop on Ask
- linked reflections separated from the library answer
- inline correction / reflection drafting
- correction apply flow with answer refresh

Reference files:

- `docs/2026-04-09-reflection-feedback-spec.md`
- `docs/2026-04-09-reflection-feedback-implementation-plan.md`

### 4.7 Automation / Watcher Layer

Completed:

- practical Inbox automation
- explicit source management inside Inbox
- `Scan now` over local intake plus configured feed / article-list sources
- retry, cooldown, and stale-state cleanup behavior

Reference files:

- `docs/2026-04-09-automation-watcher-spec.md`
- `docs/2026-04-09-automation-watcher-implementation-plan.md`

### 4.8 Relation-Aware Retrieval

Completed:

- persistent `00_System/relation-index.json`
- relation extraction over compiled wiki notes
- compile-triggered relation artifact refresh
- relation-aware Ask expansion after lexical anchors
- visible relation trace in Ask API and Workbench UI

Reference files:

- `docs/2026-04-10-relation-aware-retrieval-spec.md`
- `docs/2026-04-10-relation-aware-retrieval-implementation-plan.md`

### 4.9 Multimodal Ingestion

Completed:

- shared multimodal detection helpers
- local `pptx` raw bundle support
- local image raw bundle support for:
  - `png`
  - `jpg`
  - `jpeg`
  - `webp`
- controlled multimodal import error boundaries
- first-pass image summary contract with conservative review posture
- explicit Pillow runtime dependency for image support

Reference files:

- `docs/2026-04-10-multimodal-ingestion-spec.md`
- `docs/2026-04-10-multimodal-ingestion-implementation-plan.md`
- `docs/2026-04-10-graphify-multimodal-code-reuse-audit.md`

### 4.10 Image OCR And Screenshot Understanding

Completed:

- Apple Vision as the primary local OCR path on macOS
- fallback to the bounded image summary path when Vision OCR is unavailable or fails
- OCR-aware image `content.md` sections
- OCR metadata fields for engine, attempt state, status, text presence, interpretation mode, and image kind guess

Reference files:

- `docs/2026-04-10-image-ocr-screenshot-understanding-spec.md`
- `docs/2026-04-10-image-ocr-screenshot-understanding-implementation-plan.md`

### 4.11 Workbench V2 Shell And Navigation

Completed:

- `首頁` is the 提問工作台 and the primary working surface
- `摘要` carries the former dashboard-like overview content
- primary navigation uses Traditional Chinese labels
- the homepage is organized vertically into top / middle / bottom regions
- the current Workbench is styled as a desktop-first shell rather than a generic browser dashboard

Reference files:

- `docs/2026-04-10-workbench-v2-design-spec.md`
- `docs/2026-04-11-workbench-v2-implementation-plan.md`

## 5. Current Verified Baseline

As of this roadmap update, the verified baseline is:

- import pipeline works
- wiki compile works
- `import -> compile` runs in one top-level command
- local Workbench UI runs on localhost
- grounded Query / Ask works inside the Workbench
- Workbench Inbox can `Scan now` across:
  - local intake
  - configured RSS / feed sources
  - configured article-list-page sources
- Inbox source edits are persisted before scan runs
- automation retry and stale-state behavior are implemented for the practical automation layer
- relation artifact builds from compiled wiki notes
- compile refreshes the relation artifact after wiki updates
- Ask now uses bounded relation-aware expansion after lexical anchors
- Ask results expose visible relation trace alongside source trace
- raw import now supports first-pass `pptx` and bounded image ingestion
- raw image import now uses Apple Vision OCR first on macOS and falls back safely when Vision OCR is unavailable or fails
- image `content.md` now includes OCR-aware sections for source summary, structural summary, OCR summary, OCR text, screenshot signals, and extraction notes
- image raw bundle metadata now records OCR engine, OCR attempt state, OCR status, OCR text presence, interpretation mode, and image kind guess
- Workbench V2 shell navigation is in Traditional Chinese
- `首頁` is the 提問工作台
- `摘要` carries the old dashboard-style overview
- the homepage layout is top / middle / bottom
- the shell is desktop-first
- follow-up controls stay disabled until an Ask result has grounded note evidence
- local insufficient-evidence Ask fallback copy is now in Traditional Chinese
- tests pass
- health check passes

Verified commands used recently:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_query_ask tests.test_health_check -v
python3 -m unittest tests.test_vision_ocr tests.test_image_adapter tests.test_import_bundle tests.test_multimodal_detect tests.test_wiki_compile tests.test_query_ask -v
python3 tools/health_check.py .
python3 tools/run_workbench.py
```

## 6. Approved Build Order

The approved delivery order is:

1. Foundation and data contracts
2. Multi-format import pipeline
3. Wiki compile pipeline
4. External workbench UI
5. Query / ask layer
6. Reflection / feedback layer
7. Automation / watcher layer
8. Relation-aware retrieval
9. Multimodal ingestion
10. Image OCR and screenshot understanding
11. Workbench V2 redesign

This order should not be reversed unless there is a strong reason.

## 7. Why This Order Exists

### 7.1 Workbench UI before query

The user explicitly wants a usable external interface for all non-Obsidian work.

That means the next phase should not be a deeper backend feature first. The next phase should make the current import and compile capabilities usable through UI.

### 7.2 Query after workbench

Once the workbench exists, query becomes much easier to test and reason about because there is already a visible operational surface for:

- recent imports
- compile outputs
- bundle status
- system health

### 7.3 Reflection after query

Personal reflection and feedback should come after the user has started actually using the source-grounded wiki.

This avoids designing a reflection layer too early and keeps the source-grounded core clean.

### 7.4 Automation last

Background automation, watchers, and batch jobs are multipliers. They should be added after the manual and UI-based workflows feel correct.

## 8. Current Phase

### Phase 9: Multimodal Ingestion

This phase is now delivered and should be treated as the current importer baseline.

The importer now supports:

- `pptx`
- bounded first-pass image import

while keeping the existing raw bundle contract and downstream compile / Ask flow intact.

The purpose of this phase is:

- make slide decks usable inside the same library workflow
- make images and screenshots first-class intake instead of reserved errors
- stay honest about image quality limits instead of pretending full OCR / vision understanding already exists
- absorb only the Graphify engine parts that genuinely help intake

### This phase covers

- shared multimodal detection helpers
- `pptx` extraction into raw bundles
- bounded image summary import into raw bundles
- conservative confidence and review semantics for image imports
- controlled import-boundary errors for malformed multimodal files

### Phase 10: Image OCR And Screenshot Understanding

This phase is now delivered and should be treated as the current image baseline.

The importer now supports:

- Apple Vision OCR as the primary local OCR path on macOS
- safe fallback that preserves the bounded structural summary path while keeping OCR-aware sections in a warning-state when Vision OCR is unavailable or fails
- OCR-aware `content.md` sections for image bundles
- explicit OCR-related metadata fields in raw bundle metadata

### Phase 11: Workbench V2 Shell And Homepage

This phase is now delivered and should be treated as the current product-surface baseline.

The Workbench now supports:

- `首頁` as the 提問工作台 and primary work surface
- `摘要` as the former dashboard-style overview page
- Traditional Chinese primary navigation
- a top / middle / bottom homepage layout
- a desktop-first shell posture for the local app

## 9. Phase Boundaries

### Phase 4: Workbench UI

Definition of done:

- user can import from a UI
- user can see bundle results from a UI
- user can see compile outputs from a UI
- user can see health status from a UI
- user can configure model routing locally

### Phase 5: Query / Ask Layer

Definition of done:

- user can ask questions against the current wiki
- system can retrieve relevant synthesis and small notes
- answers stay grounded in existing wiki knowledge
- answers show note grounding and source lineage
- insufficient evidence results in a clear abstention

### Phase 6: Reflection / Feedback Layer

Definition of done:

- user can ask on one page, read the library answer, and keep reflections separate from that answer
- user can attach reflection or feedback without polluting source-grounded wiki
- reflection notes can link to wiki notes cleanly
- user can draft and confirm a correction or interpretation inline on the Ask page
- user feedback can trigger later refinement pathways
- a confirmed correction refreshes the Ask answer immediately

### Phase 7: Automation / Watcher Layer

Definition of done:

- user can manage sources inside Inbox
- `Scan now` scans local intake and configured sources together
- duplicates are filtered out reasonably before `import + compile`
- scan results stay understandable inside Inbox without a new page
- retry state is visible and bounded
- automation remains lightweight and does not become mandatory for normal use

### Phase 8: Relation-Aware Retrieval

Definition of done:

- the system builds a relation artifact from compiled wiki notes
- compile refreshes the relation artifact after wiki updates
- Ask expands through `derived-from` and `shares-source` only after lexical anchors exist
- relation expansion stays supplemental and does not override abstention
- Ask exposes a compact `relation_trace` in the API and Workbench UI
- multimodal remains explicitly out of scope for this delivered phase

### Phase 9: Multimodal Ingestion

Definition of done:

- `pptx` imports become real raw bundles instead of reserved errors
- supported image imports become real raw bundles instead of reserved errors
- multimodal imports preserve the existing `source.* -> content.md -> metadata.md -> assets/` contract
- malformed multimodal inputs fail at the importer boundary with controlled errors
- image imports remain explicit about confidence and review requirements
- compile and Ask continue to work on top of the same raw bundle pipeline

### Phase 11: Workbench V2 Shell And Homepage

Definition of done:

- `首頁` becomes the main Ask workspace
- `摘要` absorbs the old dashboard-like overview content
- primary navigation is in Traditional Chinese
- the homepage is organized into prompt, answer, evidence, and follow-up regions
- the shell feels desktop-first rather than like a generic localhost utility

## 10. Things We Are Explicitly Avoiding

Do not drift into these unless explicitly re-approved:

- heavy evaluator score factories
- multi-user system design
- replacing Obsidian as the main knowledge workspace
- turning every compile into a long multi-pass optimization process
- overbuilding automation before the workbench and query layers exist

## 11. Current Recommended Rule For Future Sessions

When a new implementation turn begins:

1. Read this roadmap.
2. Read `00_System/Execution Rules.md`.
3. Read the spec for the current phase.
4. Read the implementation plan for the current phase.
5. Only then start changing code.

If there is uncertainty, prefer the next incomplete phase in this roadmap over inventing a new side path.

## 12. Current Next Action

The next action should be:

`Use the delivered Workbench V2 shell and homepage baseline, then decide whether the next priority is desktop packaging, deeper connector expansion, or another adjacent product-hardening lane.`

## 13. Future Adoption Direction

Phase 9, Phase 10, and the first Workbench V2 redesign pass are now delivered.

The next meaningful capability expansion should not be a graph UI.

It should be selective adoption of Graphify-inspired engine capabilities:

- cache-first incremental processing
- watcher behavior split by cost
- explicit relation extraction schema
- confidence-labeled relations
- deeper multimodal quality after the current bounded first pass

Reference:

- `docs/2026-04-09-graphify-selective-adoption-note.md`
- `docs/2026-04-09-automation-watcher-spec.md`
- `docs/2026-04-10-relation-aware-retrieval-spec.md`
- `docs/2026-04-10-relation-aware-retrieval-implementation-plan.md`
- `docs/2026-04-10-multimodal-ingestion-spec.md`
- `docs/2026-04-10-multimodal-ingestion-implementation-plan.md`
- `docs/2026-04-10-graphify-multimodal-code-reuse-audit.md`
- `docs/2026-04-10-image-ocr-screenshot-understanding-spec.md`
- `docs/2026-04-10-image-ocr-screenshot-understanding-implementation-plan.md`
- `docs/2026-04-10-workbench-v2-design-spec.md`
- `docs/2026-04-11-workbench-v2-implementation-plan.md`
