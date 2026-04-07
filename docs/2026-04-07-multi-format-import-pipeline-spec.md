# Multi-Format Import Pipeline Specification

**Status:** Draft v1 approved for implementation baseline  
**Date:** 2026-04-07  
**Project:** Infinite Lore

## 1. Purpose

This subsystem defines how `Infinite Lore` ingests common external file formats and normalizes them into Markdown-first raw bundles.

The goal is not only file conversion. The goal is to:

- preserve the original source file
- produce AI-friendly normalized Markdown
- record conversion metadata and quality signals
- keep extracted assets attached to the same import unit
- provide a stable input contract for later `wiki` compilation

This importer is part of the `raw` layer and is the formal intake path for external source material.

## 2. Design Goals

The import pipeline must:

- accept multiple common source formats
- preserve the original source without rewriting it
- normalize output into a consistent `content.md`
- record origin, conversion, and review metadata in `metadata.md`
- support future format growth without redesigning the whole system
- optimize for AI usability over perfect visual fidelity
- retain useful source structure where possible

The normalization priority is:

`AI-friendly Markdown first, structure preserved where reasonably possible`

## 3. Supported Format Scope

The long-term target coverage includes:

- `docx`
- `pptx`
- `pdf`
- `txt`
- `md`
- `html`
- web article captures
- images through OCR

This set reflects the common document and content formats expected in real daily use.

## 4. Bundle Contract

Every imported source becomes a bundle folder.

The bundle is the formal storage unit for a single imported source.

Example:

```text
20_Raw/inbox/2026-04-07-some-article/
├── source.pdf
├── content.md
├── metadata.md
└── assets/
```

Another example:

```text
20_Raw/inbox/2026-04-07-market-report/
├── source.pptx
├── content.md
├── metadata.md
└── assets/
    ├── slide-01.png
    └── slide-02.png
```

Bundle rules:

- `source.*` keeps the original imported file
- `content.md` is the normalized Markdown used by downstream AI workflows
- `metadata.md` records import, source, and conversion details
- `assets/` stores extracted images, page renders, OCR support files, and related artifacts
- bundles enter through `20_Raw/inbox/`
- after normalization and review, bundles can move to `20_Raw/done/<domain>/`

## 5. Bundle File Semantics

### 5.1 `source.*`

This is the preserved original file.

Rules:

- keep original filename extension where practical
- do not rewrite source contents in place
- do not replace the source file with the Markdown output

### 5.2 `content.md`

This is the normalized Markdown payload.

Rules:

- it is the primary downstream input for `wiki` compilation
- it should be clean, segmented, and AI-friendly
- it should preserve useful structure when possible
- it should not try to mimic every visual detail of the original document

### 5.3 `metadata.md`

This is the control note for the bundle.

Rules:

- it must be present for every bundle
- it records source identity, conversion state, quality signals, and assets
- later health checks and compilers may rely on it before using `content.md`

### 5.4 `assets/`

This folder stores extracted secondary material.

Examples:

- page renders from PDF
- extracted slide images from PPTX
- OCR intermediate images
- article lead images

Rules:

- assets support traceability and review
- assets are optional, but the folder should be available when needed

## 6. Importer Architecture

The importer uses a shared pipeline with format-specific adapters.

It should not be implemented as several unrelated one-off converters.

The architecture has five parts.

### 6.1 Import Coordinator

The coordinator accepts the import request and determines:

- source path
- source format
- `primary_domain`
- `related_domains`
- `privacy`
- suggested bundle slug or title

It coordinates the pipeline but does not perform content extraction itself.

### 6.2 Format Adapter

Each format uses an adapter, but every adapter must output a compatible intermediate result.

Planned adapters:

- text and markdown adapter
- HTML and article adapter
- DOCX adapter
- PPTX adapter
- PDF adapter
- image adapter

The adapter is responsible for extracting usable content blocks, not for writing the final bundle format.

### 6.3 Markdown Normalizer

This is the shared normalization layer.

Its responsibilities include:

- heading normalization
- paragraph segmentation
- list cleanup
- table preservation or simplification
- image placeholder insertion
- source markers such as page or slide references

This layer creates the final Markdown shape expected in `content.md`.

### 6.4 Bundle Writer

The bundle writer creates:

- `source.*`
- `content.md`
- `metadata.md`
- `assets/`

It also writes the bundle to the correct vault location.

### 6.5 Quality Marker

The quality marker records whether conversion is trustworthy enough for direct downstream use.

It sets:

- conversion status
- extraction confidence
- review requirement
- warnings

## 7. Metadata Contract

Every import bundle must include a `metadata.md` note with frontmatter.

Minimum structure:

```yaml
---
id:
title:
layer: raw
note_type: raw-bundle
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []

source_format:
source_filename:
source_path:
source_type:
source_ref:
imported_at:
published_at:
content_hash:

conversion_status:
converter:
extraction_confidence:
review_required:
warnings: []

asset_paths: []
---
```

## 8. Metadata Field Semantics

### 8.1 Shared system fields

- `id`
- `title`
- `layer`
- `note_type`
- `primary_domain`
- `related_domains`
- `privacy`
- `status`
- `created_at`
- `updated_at`
- `source_refs`

These fields allow the raw bundle to participate in the broader Infinite Lore note system.

### 8.2 Source identity fields

- `source_format`
- `source_filename`
- `source_path`
- `source_type`
- `source_ref`
- `imported_at`
- `published_at`
- `content_hash`

These fields explain what was imported, from where, and when.

### 8.3 Conversion control fields

- `conversion_status`
- `converter`
- `extraction_confidence`
- `review_required`
- `warnings`

These fields explain how trustworthy the conversion is and whether a human should inspect it.

### 8.4 Asset linkage fields

- `asset_paths`

These fields point to extracted secondary files inside the bundle.

## 9. Conversion Quality Rules

The importer must be explicit about output reliability.

### 9.1 `conversion_status`

Allowed values:

- `pending`
- `converted`
- `needs-review`
- `failed`

### 9.2 `extraction_confidence`

Allowed values:

- `high`
- `medium`
- `low`

### 9.3 `review_required`

Allowed values:

- `true`
- `false`

### 9.4 Format-default guidance

- `txt` and `md` should usually default to `high`
- `html` and web article extraction should usually default to `medium`
- `docx` should often land in `medium` or `high`
- `pdf` should default conservatively to `medium`
- `pptx` should usually default to `medium`
- image OCR should usually default to `low` or `medium`

### 9.5 Warning examples

Examples of warning strings:

- `table structure simplified`
- `image-only page detected`
- `ocr confidence low`
- `slide speaker notes not extracted`
- `article body may include boilerplate`

## 10. Markdown Normalization Rules

The normalized Markdown should prioritize downstream reasoning quality.

The normalizer should preserve when possible:

- heading hierarchy
- paragraphs
- bullet lists
- numbered lists
- tables when structurally reasonable
- slide boundaries
- page references
- image references

The normalizer should prefer simplification when a perfect visual match would reduce clarity or increase noise.

Examples:

- flattened but readable tables are better than broken table syntax
- explicit slide markers are better than pretending PPTX content is a normal document
- image placeholders are better than silently dropping important figures

## 11. Format Maturity Tiers

All targeted formats belong in the same architecture, but not all need equal maturity in the first implementation.

### 11.1 Tier 1: Must be solid in the first implementation

- `txt`
- `md`
- `html`
- web article capture

Reason:

- these are closest to text-first inputs
- they are the fastest way to unlock real `raw -> wiki -> artifact` workflows

### 11.2 Tier 2: Included early, but may be conservative

- `pdf`
- `docx`

Reason:

- these are too common to postpone
- structure quality may vary
- first implementation should favor usable output plus clear quality flags over perfect structural fidelity

### 11.3 Tier 3: Architecture-ready, maturity can come later

- `pptx`
- image OCR

Reason:

- both often require heavier extraction logic and more careful ordering or review
- the first implementation should reserve adapter interfaces and bundle support without overpromising quality

## 12. Daily Usage Model

The importer should feel like "send this source into the system," not "run a brittle conversion utility."

### 12.1 Importing a web article

The expected flow:

- capture the article source
- create the bundle
- store the original source
- generate `content.md`
- generate `metadata.md`
- mark quality level
- pass the bundle into later knowledge workflows

### 12.2 Importing a PDF

The expected flow:

- preserve the PDF
- extract text into `content.md`
- store page or image assets when needed
- mark whether review is required

### 12.3 Importing a DOCX or PPTX

The expected flow is structurally identical:

- preserve the source file
- normalize into Markdown
- attach metadata and assets
- rely on `content.md` as the standard downstream input

### 12.4 Importing an image

The image path is more conservative:

- preserve the original image
- OCR into Markdown
- mark likely review needs
- keep warnings explicit

## 13. Downstream Integration

The importer exists to support the rest of Infinite Lore.

The intended downstream chain is:

`source file -> raw bundle -> normalized markdown -> wiki compile -> brainstorming -> artifact`

This means:

- `wiki` compilation should consume bundle-standardized Markdown, not raw file formats directly
- `brainstorming` should operate on knowledge and questions, not on arbitrary binary files
- `artifacts` should be created from processed knowledge, not from unstructured source imports

## 14. Implementation Boundaries

The first implementation of this subsystem should include:

- bundle creation logic
- shared metadata structure
- shared Markdown normalization contract
- adapters for `txt`, `md`, `html`, and web article input
- basic usable support for `pdf` and `docx`
- adapter interface reservation for `pptx` and image OCR

The first implementation should not require:

- perfect layout fidelity
- OCR excellence across all image types
- full slide design reconstruction from PPTX
- one hundred percent clean table recovery in every PDF

## 15. Summary

The multi-format import pipeline is a normalization subsystem, not just a converter.

Its job is to preserve original sources, produce AI-friendly Markdown bundles, record quality and traceability metadata, and provide a stable intake contract for later Infinite Lore knowledge workflows.
