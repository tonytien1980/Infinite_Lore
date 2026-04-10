# Graphify Phase 8 Code Reuse Audit

**Status:** Active implementation-prep note  
**Date:** 2026-04-10  
**Project:** Infinite Lore  
**Reference repo:** `safishamsi/graphify`  
**Audited commit:** `af3a3d2`

## 1. Purpose

This note records which parts of `Graphify` are worth reusing or adapting for the next `Infinite Lore` phase:

- relation-aware retrieval
- relation artifact generation
- later multimodal expansion

The purpose is practical speed.

When Phase 8 implementation starts, this note should answer:

- which Graphify files are worth reading first
- which modules are good direct or near-direct reuse candidates
- which modules are only good as architecture references
- which modules should not be pulled into `Infinite Lore`

## 2. Files Reviewed

Primary sources reviewed from the Graphify repo:

- `README.md`
- `ARCHITECTURE.md`
- `graphify/cache.py`
- `graphify/watch.py`
- `graphify/extract.py`
- `graphify/build.py`
- `graphify/ingest.py`
- `graphify/security.py`
- `graphify/serve.py`
- `graphify/validate.py`
- `tests/test_confidence.py`
- `tests/test_watch.py`
- `tests/test_cache.py`

## 3. Main Audit Conclusion

For Phase 8, `Graphify` is most useful as:

- a schema and pipeline reference
- a confidence-model reference
- a cache / validation / safety-pattern source

It is not most useful as:

- a direct relation-extraction engine for wiki notes
- a graph-first product shell
- a graph visualization starting point

The key reason is simple:

`Graphify` is centered on corpus extraction into a general graph, while `Infinite Lore` Phase 8 is centered on note-to-note relations that improve `Ask`.

That means the best reuse target is:

`engine patterns, validation patterns, and confidence conventions`

not:

`whole-module transplant`

## 4. Best Reuse Candidates For Phase 8

### 4.1 `graphify/validate.py`

Recommendation:

- `adapt heavily`

Why:

- Phase 8 introduces a new generated artifact: `relation-index.json`
- a schema validator is a good fit for keeping that artifact strict and explainable
- Graphify already separates extraction validation from graph assembly cleanly

Best reuse idea:

- copy the structural idea, not necessarily the exact schema
- keep a tiny validator for:
  - required note fields
  - required edge fields
  - valid confidence values
  - valid relation types

Why this is high value:

- low integration risk
- high correctness value
- directly supports a note-based relation artifact

### 4.2 Confidence-label conventions from `README.md`, `ARCHITECTURE.md`, and `tests/test_confidence.py`

Recommendation:

- `reuse concept directly`

Why:

- `EXTRACTED`
- `INFERRED`
- `AMBIGUOUS`

already map cleanly onto the `Infinite Lore` relation-first plan.

Best reuse idea:

- keep the same label vocabulary
- adapt the meaning to wiki-note relations
- optionally add a numeric `confidence_score` later, but not required in the first version

Why this is high value:

- improves Ask trust boundaries immediately
- consistent with the user's prior interest in “what is found vs guessed”

### 4.3 `graphify/build.py`

Recommendation:

- `reuse architecture pattern only`

Why:

- its real value is the separation:
  - validated extraction input
  - graph assembly
  - no hidden shared state

Best reuse idea:

- mirror the shape:
  - read notes
  - emit note/edge dicts
  - validate artifact
  - save artifact

Do not reuse directly:

- the NetworkX-specific assembly logic
- graph edge storage format as-is

Why:

- Phase 8 does not need a general graph object yet
- JSON artifact generation is enough

### 4.4 `graphify/cache.py`

Recommendation:

- `selective reuse later in Phase 8 or Phase 8.5`

Why:

- the file-hash and atomic-write patterns are solid
- the Markdown frontmatter-insensitive hash is especially interesting for note-based systems

Best reuse idea:

- relation artifact rebuild cache
- skip rebuild when only irrelevant metadata changes
- atomic write for `relation-index.json`

Directly useful detail:

- Graphify hashes Markdown body content separately from frontmatter
- for `Infinite Lore`, that idea may help avoid unnecessary relation rebuilds when only non-structural metadata changes

Not required on day one:

- Phase 8 can still start with full rebuild after compile

### 4.5 `graphify/security.py`

Recommendation:

- `adapt selectively when touching remote fetch or future multimodal ingest`

Why:

- the URL validation and safe fetch boundaries are good
- the module separates:
  - URL validation
  - safe fetch
  - path validation
  - label sanitization

Best reuse idea:

- future hardening around connector fetches
- later multimodal remote asset ingestion

For Phase 8 specifically:

- lower priority than `validate.py`
- still worth reading before any new external fetch surface is added

## 5. Good Conceptual References, But Not Direct Reuse

### 5.1 `graphify/extract.py`

Recommendation:

- `concept only`

Why:

- it is built for code and corpus extraction with tree-sitter and broader semantic extraction
- Phase 8 relation-first work is simpler and should derive mostly from existing wiki metadata and lineage

Best reuse idea:

- extraction output discipline
- stable IDs
- one extractor output feeding one builder

Do not reuse directly:

- language extraction logic
- AST-oriented node building
- code-specific relation extraction

### 5.2 `graphify/watch.py`

Recommendation:

- `concept only for later`

Why:

- we already selectively absorbed the split-by-cost watcher idea into Phase 7 thinking
- Phase 8 is not a watcher phase

Best reuse idea:

- later relation rebuild triggers that separate:
  - cheap note-state checks
  - expensive relation regeneration

### 5.3 `graphify/ingest.py`

Recommendation:

- `later multimodal reference`

Why:

- its URL-type classification and fetch flow are useful
- but Phase 8 is not the multimodal implementation phase

Best reuse idea:

- future `pptx` / image / richer source handling
- later remote-content classification patterns

## 6. Modules Not Worth Pulling Into Phase 8

### 6.1 `graphify/serve.py`

Do not adopt in Phase 8.

Why:

- MCP graph serving is interesting, but it is not required for a note-based relation artifact
- it would add a second interaction surface before the core relation-aware Ask behavior is proven useful

### 6.2 Export / graph presentation modules

Do not adopt in Phase 8:

- `graphify/export.py`
- `graphify/report.py`
- graph visualization outputs

Why:

- these are graph-first affordances
- the approved direction is still `Ask-first / library-first`

### 6.3 Clustering / analysis modules

Do not adopt in Phase 8:

- `graphify/cluster.py`
- `graphify/analyze.py`

Why:

- community detection is valuable later
- but it is not needed for the first bounded relation-aware retrieval pass

## 7. Phase 8 Reuse Recommendation

The recommended Phase 8 reuse order is:

1. Read `graphify/validate.py`
2. Reuse the `EXTRACTED / INFERRED / AMBIGUOUS` confidence model
3. Mirror the `extract -> validate -> build -> save` module separation from `graphify/build.py`
4. Keep `graphify/cache.py` open as the first follow-up optimization source
5. Defer `extract.py`, `watch.py`, and `ingest.py` to later relation or multimodal expansions

## 8. Practical Build Advice

When Phase 8 implementation starts, the fastest sane path is:

1. Build a tiny `tools/relation_index.py`
2. Give it a strict JSON schema and validator
3. Use existing wiki lineage fields first
4. Add confidence labels from the start
5. Make Ask consume the relation artifact only after lexical anchors exist

That path gets the best part of Graphify's architecture without dragging in Graphify's whole product identity.

## 9. Bottom Line

For Phase 8:

- `Graphify` should be treated as a strong engine reference
- the best direct borrowing target is validation and confidence discipline
- the best structural borrowing target is pipeline separation
- the wrong move is copying graph UI or full graph runtime machinery too early

In one sentence:

`Borrow Graphify’s discipline, not its shell.`
