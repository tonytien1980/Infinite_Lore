# Relation-Aware Retrieval Specification

**Status:** Draft v1 for review  
**Date:** 2026-04-10  
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next knowledge-layer expansion after Phase 7.

The goal is to make `Ask` more accurate, more trustworthy, and more structurally grounded by adding a formal relation layer between compiled wiki notes.

This phase is intentionally:

- `relation-first`
- `Ask-first`
- `library-first`

It is not a graph-visualization phase.

It is also not the phase that fully implements multimodal ingestion.

## 2. Why This Is The Next Phase

`Infinite Lore` already has:

- multi-format raw ingest
- source-grounded wiki compile
- grounded `Ask / Query`
- reflection and correction feedback
- practical `Scan now` automation

The most meaningful next quality jump is not “more UI.”

It is:

- better internal structure between notes
- better retrieval expansion for Ask
- clearer confidence boundaries for linked knowledge

This phase exists to improve answer quality before expanding surface area again.

## 3. Approved Direction

The approved next direction is:

`Phase 8 = Relation-first retrieval expansion`

Meaning:

- first build a formal relation artifact beside the wiki layer
- then use that artifact to improve Ask retrieval and traceability
- keep multimodal as the next adjacent expansion, but not the first implementation target in this phase

## 4. Core Principle

The system should retrieve by knowledge structure, not only by keyword overlap.

But that structure must stay:

- explicit
- source-aware
- confidence-labeled
- explainable

The system must never bootstrap an answer from weak relation guesses alone.

## 5. Current Baseline

The current system already has:

- `source_refs`
- `raw_bundle_ref`
- `compiled_from`
- `note_type`
- `primary_domain`
- grounded retrieval across compiled wiki notes

The current system does not yet have:

- an explicit machine-readable relation artifact
- typed note-to-note relations
- relation confidence labels
- relation-aware Ask expansion
- multimodal ingest beyond the existing text-first multi-format set

## 6. In Scope

This phase should include:

- a persistent relation artifact generated from compiled wiki notes
- a small initial relation schema
- confidence labels on extracted relations
- relation-aware candidate expansion inside `Ask`
- visible relation trace support for Ask responses
- compile-triggered relation artifact refresh

This phase may include:

- a full relation rebuild after compile, if that keeps the implementation simple
- a minimal relation trace section in the Ask UI

## 7. Out Of Scope

This phase should not include:

- graph UI
- graph exports
- Neo4j or external graph backends
- general semantic link mining across the whole vault
- reflection-entry relations as grounded answer evidence
- `pptx` implementation
- image OCR implementation
- screenshot understanding implementation

Those remain future expansion targets.

## 8. Relation Artifact

The first version should create one persistent machine-readable artifact:

- `00_System/relation-index.json`

This artifact is:

- generated
- derived from compiled wiki notes
- not the primary authoring surface

The artifact should contain:

```json
{
  "generated_at": "2026-04-10T00:00:00Z",
  "notes": [
    {
      "path": "30_Wiki/ai-application/example--synthesis.md",
      "note_type": "synthesis",
      "primary_domain": "ai-application"
    }
  ],
  "edges": [
    {
      "source_note": "30_Wiki/ai-application/example--concept--foo.md",
      "target_note": "30_Wiki/ai-application/example--synthesis.md",
      "relation": "derived-from",
      "confidence": "EXTRACTED",
      "evidence_type": "compiled_from",
      "evidence_ref": "30_Wiki/ai-application/example--synthesis.md",
      "updated_at": "2026-04-10T00:00:00Z"
    }
  ]
}
```

## 9. Initial Relation Types

The first version should stay intentionally narrow.

### 9.1 `derived-from`

Use when a compiled note explicitly points to another compiled note through existing lineage fields.

Typical examples:

- a small note derived from a synthesis note
- a note whose `compiled_from` points at a synthesis note

Confidence:

- `EXTRACTED`

### 9.2 `shares-source`

Use when two compiled notes share overlapping source lineage.

Typical examples:

- overlapping `source_refs`
- matching `raw_bundle_ref`

Confidence:

- `INFERRED`

### 9.3 `AMBIGUOUS`

The label should exist in the schema from the start, but the first extraction pass does not need to generate many ambiguous edges.

It is reserved for later weak or multimodal relation work.

The first Ask phase should not use `AMBIGUOUS` edges for answer expansion by default.

## 10. Confidence Model

The system should support three confidence labels:

- `EXTRACTED`
- `INFERRED`
- `AMBIGUOUS`

The operational meaning should be:

- `EXTRACTED`
  - relation came from explicit stored structure
- `INFERRED`
  - relation came from bounded derivation over stored lineage
- `AMBIGUOUS`
  - relation is plausible but weak and should not drive the answer by itself

## 11. Relation Extraction Rules

The first extraction pass should only read compiled wiki notes in `30_Wiki/`.

It should ignore:

- reflection entries
- correction proposals
- journal notes
- project logs
- artifacts

The relation layer is for grounded knowledge notes first.

## 12. Ask Retrieval Model

The current Ask flow should remain structurally intact:

1. lexical retrieval over compiled notes
2. grounded candidate selection
3. answer generation or abstention

The new relation-aware flow should be:

1. lexical retrieval over compiled notes
2. choose a small anchored set of strong notes
3. expand from those anchors through relation edges
4. re-rank expanded notes with confidence-aware bonuses
5. keep traceability visible

Two hard rules:

1. There must be at least one lexical anchor note before relation expansion matters.
2. Relations alone must not override an otherwise insufficient-evidence outcome.

## 13. Ask Output Changes

The first version should add relation support without making Ask noisy.

Preferred additions:

- a `relation_trace` field in Ask responses
- optional note-level indication that a supporting note arrived through:
  - direct lexical match
  - `derived-from`
  - `shares-source`

This should help the user understand why a note was pulled in.

## 14. Compile Integration

The first version should refresh the relation artifact when compile changes the wiki.

For simplicity, Phase 8 may use:

- full relation rebuild after compile

This is acceptable because:

- the system is still single-user
- the current dataset is modest
- correctness matters more than premature optimization here

Incremental relation caching can come later if needed.

## 15. Multimodal Boundary

Multimodal remains the next adjacent expansion, but not the first code target of this phase.

The future multimodal lane should cover:

- `pptx`
- image OCR
- image-heavy note extraction
- screenshot and diagram intake

The purpose of documenting it here is boundary clarity, not immediate implementation.

## 16. Relationship To Graphify

This phase should absorb only the Graphify ideas that directly improve Ask quality:

- explicit relation artifacts
- confidence labels
- relation-aware retrieval

This phase should not absorb:

- graph-first workflow
- graph visualization
- graph export as a primary surface

## 17. Success Criteria

Phase 8 succeeds when:

- the system can build a relation artifact from compiled wiki notes
- Ask can use `derived-from` and `shares-source` edges to improve candidate retrieval
- relation expansion stays bounded by lexical anchors
- answer trust boundaries stay explicit
- relation trace is visible enough to explain why extra notes were pulled in
- the phase improves Ask quality without turning the product into a graph tool
