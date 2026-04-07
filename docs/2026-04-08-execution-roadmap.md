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

## 5. Current Verified Baseline

As of this roadmap update, the verified baseline is:

- import pipeline works
- wiki compile works
- `import -> compile` runs in one top-level command
- tests pass
- health check passes

Verified commands used recently:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_health_check -v
python3 tools/health_check.py .
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

## 8. Immediate Next Phase

### Phase 4: External Workbench UI

This is the next priority.

The purpose of the workbench is:

- provide a proper UI/UX for non-Obsidian operations
- support testing and inspection more easily
- expose the current system without requiring terminal use for normal operation

### The first workbench should cover

- dashboard
- import flow
- bundle inspection
- compile result inspection
- health status

### The first workbench should not yet cover

- full chat experience
- full reflection management
- automation daemon controls
- team collaboration

## 9. Phase Boundaries

### Phase 4: Workbench UI

Definition of done:

- user can import from a UI
- user can see bundle results from a UI
- user can see compile outputs from a UI
- user can see health status from a UI

### Phase 5: Query / Ask Layer

Definition of done:

- user can ask questions against the current wiki
- system can retrieve relevant synthesis and small notes
- answers stay grounded in existing wiki knowledge

### Phase 6: Reflection / Feedback Layer

Definition of done:

- user can attach reflection or feedback without polluting source-grounded wiki
- reflection notes can link to wiki notes cleanly
- user feedback can trigger later refinement pathways

### Phase 7: Automation / Watcher Layer

Definition of done:

- system can optionally watch intake locations or run scheduled jobs
- automation remains lightweight and does not become mandatory for normal use

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

`Design and implement the first External Workbench UI for non-Obsidian operations.`
