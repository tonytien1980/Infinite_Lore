# Graphify Selective Adoption Note

**Status:** Active future-direction note  
**Date:** 2026-04-09  
**Project:** Infinite Lore

## 1. Purpose

This note records which `Graphify` ideas and modules are worth selectively adopting into `Infinite Lore`.

The goal is not to transplant Graphify as a second product shell.

The goal is to selectively absorb the parts that materially improve:

- multimodal ingestion
- relation-aware retrieval
- incremental processing
- watcher and cache behavior
- answer trust and evidence labeling

## 2. Why This Note Exists

`Infinite Lore` already has a working foundation:

- raw import
- wiki compile
- grounded Ask / Query
- reflection and correction feedback
- local Workbench UI

However, two capability gaps remain clear:

1. The current importer is multi-format, but not yet fully multimodal.
2. The current wiki layer has lineage and links, but not a formal relation layer.

`Graphify` is relevant because it provides a clean reference architecture for:

- extraction into `nodes + edges`
- confidence labeling
- cache-based incremental rebuilds
- watch-driven updates

## 3. Current Infinite Lore State

### 3.1 Already present

- text-first multi-format import:
  - `txt`
  - `md`
  - `html`
  - web article URLs
  - `docx`
  - `pdf`
- source-grounded compile into:
  - `synthesis`
  - `concept`
  - `framework`
  - `question`
- source lineage:
  - `source_refs`
  - `raw_bundle_ref`
  - `compiled_from`
- grounded Ask / Query over compiled wiki notes
- reflection and correction on the Ask page

### 3.2 Partially present

- relationship signals through frontmatter and lineage
- candidate links in synthesis notes
- note-to-note linking through existing wiki structure

### 3.3 Missing

- `pptx` import
- image OCR import
- explicit relation schema
- typed relations such as:
  - `derived-from`
  - `supports`
  - `related-to`
  - `contrasts-with`
  - `mentions`
- relation confidence labels
- relation-aware retrieval for Ask
- persistent relation artifacts such as a graph index

## 4. What Makes Graphify Useful Here

The most useful parts of Graphify are not its graph visualization output.

The most useful parts are:

1. extraction output discipline
2. confidence labeling
3. persistent intermediate artifacts
4. cache and watcher behavior

These can strengthen `Infinite Lore` without changing the product into a graph-first tool.

## 5. Selective Adoption Principles

`Infinite Lore` should adopt from Graphify using these rules:

1. Borrow capabilities, not product identity.
2. Prefer relation-aware retrieval over graph visualization.
3. Keep `Ask-first / library-first` as the primary user experience.
4. Keep Obsidian and the vault as the source of truth.
5. Only absorb modules that directly improve the existing roadmap.

## 6. What To Adopt

### 6.1 Adopt for Phase 7: Automation / Watcher

These are the highest-value near-term borrowings.

#### A. Cache-first incremental processing

Graphify reference:

- `graphify/cache.py`

Why it matters:

- avoids re-processing unchanged files
- lowers local compute and later API cost
- makes `Scan now` and background automation practical

Infinite Lore adoption target:

- bundle hash cache
- compile cache
- future relation extraction cache

#### B. Watcher behavior split by cost

Graphify reference:

- `graphify/watch.py`

Why it matters:

- distinguishes cheap rebuild work from expensive semantic work
- keeps watch mode usable instead of noisy or too costly

Infinite Lore adoption target:

- code-free raw folder watching
- cheap local refresh for status and file discovery
- deferred expensive reprocessing when LLM work is required

### 6.2 Adopt for the next knowledge-layer expansion

These should come after the automation / watcher layer.

#### A. Relation extraction schema

Graphify references:

- `ARCHITECTURE.md`
- `graphify/extract.py`
- `graphify/build.py`

Useful concept:

```json
{
  "nodes": [],
  "edges": [
    {
      "source": "...",
      "target": "...",
      "relation": "...",
      "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"
    }
  ]
}
```

Why it matters:

- gives Ask more than keyword matching
- improves retrieval precision through relation structure
- preserves explainable reasoning paths

Infinite Lore adoption target:

- a persistent relation artifact that sits beside the wiki layer
- relation-aware retrieval before any graph UI is considered

#### B. Confidence labels

Graphify reference:

- `EXTRACTED`
- `INFERRED`
- `AMBIGUOUS`

Why it matters:

- supports anti-hallucination goals
- helps Ask present stronger trust boundaries
- makes ambiguity visible instead of hidden

Infinite Lore adoption target:

- relation confidence on extracted links
- Ask answer sections that distinguish:
  - grounded facts
  - inferred links
  - uncertain or weakly grounded links

### 6.3 Adopt for the multimodal expansion

These should come after the relation layer design is stable.

#### A. Multimodal extraction patterns

Graphify references:

- `README.md`
- `graphify/extract.py`

Why it matters:

- aligns with the long-term importer target already defined in `Infinite Lore`
- supports screenshots, diagrams, image-heavy notes, and richer documents

Infinite Lore adoption target:

- `pptx`
- image OCR
- image-based content extraction

## 7. What Not To Adopt

The following should not be transplanted into `Infinite Lore` as primary product behavior.

### 7.1 Do not adopt Graphify's product identity

Do not turn `Infinite Lore` into:

- a graph-first explorer
- a skill-first CLI product
- a visualization-first knowledge tool

### 7.2 Do not adopt graph visualization as the next priority

`graph.html`, SVG export, or similar graph views are optional future affordances.

They are not the highest-value next step.

The higher-value step is:

`relation-aware retrieval that improves Ask`

### 7.3 Do not adopt export/report surfaces that do not strengthen daily use

Examples:

- standalone graph visualization exports
- report layers that duplicate existing Workbench surfaces
- Neo4j-oriented export paths

These may be useful later, but they are not currently aligned with the product's primary workflow.

## 8. Direct Code Reuse Guidance

Because Graphify is MIT-licensed, direct code reuse is legally possible.

Even so, the recommended strategy is selective reuse only.

### Reuse directly or adapt heavily

- cache helpers
- watcher logic patterns
- relation schema ideas
- confidence label conventions
- targeted extraction helpers where they cleanly fit the importer

### Do not wholesale copy

- the full product shell
- report generation surface
- graph export surface
- the graph-first interaction model

The goal is:

`adopt useful engine parts, keep Infinite Lore's own product shape`

## 9. Recommended Adoption Order

The approved future order should be:

1. finish Workbench V2 UX redesign
2. deliver Phase 7 Automation / Watcher
3. add selective Graphify-inspired cache and watcher behavior
4. design a formal relation layer
5. make Ask relation-aware
6. expand toward fuller multimodal ingestion
7. only then consider a graph view, if it still feels useful

## 10. Core Product Reminder

The point of adopting from Graphify is not to make `Infinite Lore` look more advanced.

The point is to make this product better at its core job:

- ingesting knowledge
- organizing it into trustworthy structure
- answering from that structure
- preserving personal use value through real daily workflows

If a borrowed Graphify capability does not improve one of those four outcomes, it should not be adopted.
