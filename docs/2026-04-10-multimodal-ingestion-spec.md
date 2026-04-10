# Multimodal Ingestion Specification

**Status:** Delivered v1
**Date:** 2026-04-10
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next adjacent phase after delivered Phase 8.

The goal is to expand `Infinite Lore` from a text-first multi-format importer into a true multimodal intake system that can safely ingest:

- `pptx`
- standalone images and screenshots

without creating a second product shell or a second ingest architecture.

## 2. Why This Is The Next Phase

`Infinite Lore` already has:

- bundle-based raw intake
- support for `txt`, `md`, `html`, `docx`, `pdf`, and web article import
- source-grounded wiki compile
- relation-aware `Ask`

The most adjacent user value jump now is:

- letting slide decks enter the same system
- letting screenshots, diagrams, and image-heavy knowledge enter the same system

This phase should deepen usable intake, not reopen graph-first product drift.

## 3. Approved Direction

The approved next direction is:

`Phase 9 = Multimodal intake on the existing raw bundle contract`

Meaning:

- keep one import pipeline
- add multimodal adapters inside that pipeline
- preserve `source.* -> content.md -> metadata.md -> assets/`
- selectively reuse `Graphify` engine parts where they are real and useful
- do not rebuild a second graph-oriented corpus system

## 4. Core Principle

Multimodal support should improve the same library workflow, not create a new one.

The system should:

- preserve the original file
- extract the most useful text and visual structure into `content.md`
- keep supporting assets in `assets/`
- record confidence and review needs in `metadata.md`
- remain compatible with the existing `compile -> Ask` flow

## 5. Current Baseline

The current importer already supports:

- `txt`
- `md`
- `html`
- web article captures
- `docx`
- `pdf`

The current importer now supports:

- `pptx`
- bounded image import for:
  - `png`
  - `jpg`
  - `jpeg`
  - `webp`

It still does not yet provide:

- rich OCR by default
- full screenshot / diagram understanding

## 6. In Scope

This phase should include:

- local `pptx` import
- local image import for:
  - `png`
  - `jpg`
  - `jpeg`
  - `webp`
- bundle-compatible multimodal metadata and assets
- one shared multimodal detection layer
- one shared multimodal extraction contract
- direct reuse or adaptation of real `Graphify` code where it cleanly fits

This phase may include:

- optional provider-backed image understanding if configured
- image-derived warnings when extraction quality is weak
- extracted embedded images from `pptx` bundles

## 7. Out Of Scope

This phase should not include:

- graph UI
- graph exports
- multimodal relation mining across the whole vault
- video ingestion
- audio ingestion
- arbitrary remote crawling of media-heavy sites
- screenshot understanding directly inside `Ask`

Those remain later expansion targets.

## 8. File-Type Scope

The first multimodal lane should cover two families.

### 8.1 `pptx`

The importer should accept local PowerPoint files and produce a normal raw bundle.

Minimum expected output:

- preserved `source.pptx`
- `content.md` with one section per slide
- extracted slide text where available
- `assets/` entries for extracted embedded images when present
- metadata warnings when extraction is partial or weak

### 8.2 Images

The importer should accept standalone image files and produce a normal raw bundle.

Minimum expected output:

- preserved original image file
- `content.md` containing:
  - extracted visible text when available
  - a concise structural summary
  - review warnings when confidence is weak
- `assets/` available for derivative support files if needed

The system should treat screenshots, diagrams, and image-heavy notes as valid first-class input.

## 9. Bundle Contract

This phase must preserve the existing bundle contract:

```text
20_Raw/inbox/<bundle>/
├── source.pptx | source.png | source.jpg | ...
├── content.md
├── metadata.md
└── assets/
```

Rules:

- do not replace the original file with derived output
- do not invent a second multimodal bundle type
- keep downstream compile compatible with existing raw bundles

## 10. Content Normalization Rules

### 10.1 PPTX normalization

The first version should normalize slides into Markdown like:

- document title
- slide-by-slide headings
- bullet text and speaker-note text when available
- references to extracted assets

The purpose is AI-usable structure, not visual-perfect deck reconstruction.

### 10.2 Image normalization

The first version should normalize images into Markdown like:

- image type or guess
- extracted visible text
- concise summary of what the image contains
- uncertainty markers when confidence is weak

This should be useful enough for later compile and Ask, even if it is not a perfect description.

## 11. Confidence And Review Rules

Multimodal extraction must remain honest.

Recommended first-pass defaults:

- `pptx` text-first extraction should usually default to `medium`
- image extraction should usually default to `low` or `medium`
- image bundles should more often require review than plain text bundles

The system should prefer:

- explicit warnings
- review-required flags
- bounded summaries

over pretending uncertain extraction is clean.

## 12. Relationship To Graphify

This phase should selectively reuse `Graphify`, but only where real reusable implementation exists.

### 12.1 Reuse directly or adapt directly

Strong candidates:

- file-type detection patterns from `graphify/detect.py`
- office and PDF conversion helper patterns from `graphify/detect.py`
- URL / binary ingest safety patterns from `graphify/ingest.py`
- stage separation discipline:
  - detect
  - extract
  - validate
  - bundle-write

### 12.2 Reference conceptually, not as direct code transplant

Useful but not a direct drop-in:

- semantic extraction flow for docs / papers / images
- image understanding posture
- confidence-labeled extraction outputs

### 12.3 Do not pretend Graphify already solves this

Important boundary:

- current `Graphify` does not provide a real `pptx` adapter
- current multimodal semantic extraction in `Graphify` is partly orchestration / skill-level behavior, not a clean reusable Python module for `Infinite Lore`

So this phase should reuse what is real, not what only exists as workflow description.

## 13. Recommended Architecture

The first implementation should use four layers.

### 13.1 Detection layer

Responsibilities:

- classify incoming files
- decide whether a file is:
  - text-like
  - office-like
  - paper-like
  - image-like
- route the source into the correct adapter

This layer is the best direct `Graphify` reuse target.

### 13.2 Adapter layer

Responsibilities:

- `pptx` adapter
- image adapter
- shared extraction result contract

Each adapter should return one consistent intermediate object, not write bundles directly.

### 13.3 Normalization layer

Responsibilities:

- turn adapter output into `content.md`
- keep source markers and asset references readable
- attach warnings and confidence

### 13.4 Bundle writer

Responsibilities:

- preserve original file
- write `content.md`
- write `metadata.md`
- write `assets/`

This should stay aligned with the existing raw bundle contract instead of creating a parallel multimodal writer.

## 14. Preferred Delivery Order Inside This Phase

Even though this phase covers both families, implementation should still sequence within one lane:

1. shared multimodal detection and bundle contract alignment
2. `pptx` adapter
3. image adapter
4. optional provider-backed enrichment if needed for image quality

This keeps the lane unified while still giving a sane internal order.

## 15. Success Criteria

Phase 9 succeeds when:

- `pptx` imports become real raw bundles instead of reserved errors
- image imports become real raw bundles instead of reserved errors
- imported multimodal bundles remain compatible with compile and Ask
- `Graphify` reuse is real and selective, not cosmetic
- the new lane makes the library more useful without turning the product into a graph tool
