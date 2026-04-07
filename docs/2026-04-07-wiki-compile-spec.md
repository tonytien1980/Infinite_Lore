# Wiki Compile Specification

**Status:** Draft v1 approved for implementation baseline  
**Date:** 2026-04-07  
**Project:** Infinite Lore

## 1. Purpose

This subsystem defines how `Infinite Lore` compiles a normalized raw bundle into maintained wiki knowledge.

Its job is not to produce a generic summary. Its job is to:

- transform raw bundle content into reusable knowledge objects
- preserve clear source lineage
- create one stable synthesis entry point per source
- optionally extract a small number of high-value reusable notes
- protect the source-grounded knowledge layer from personal interpretation drift

The compile subsystem sits between `raw` and the rest of the knowledge system.

## 2. Core Principle

The compile layer must remain `source-grounded`.

This means:

- it may summarize, abstract, and structure
- it may propose candidate links
- it may identify reusable ideas and open questions
- it must not pretend system interpretation is user interpretation
- it must not mix later personal opinions into source-grounded compile notes

This principle protects the long-term integrity of the knowledge base.

## 3. Output Model

The approved output model is a mixed strategy.

For each raw bundle, the compiler should produce:

- exactly one `synthesis` note
- optionally `0-3` smaller reusable notes

Supported smaller note types:

- `concept`
- `framework`
- `question`
- `reference` only when necessary

This model avoids two failure modes:

- one giant note with no reusable knowledge structure
- too many fragmented notes produced by aggressive slicing

## 4. Source And Interpretation Boundary

The system must preserve four different cognitive layers:

- source truth
- source-grounded structured knowledge
- personal interpretation
- later revision of personal interpretation

The compile subsystem only owns the second layer.

Hard rules:

- raw source material must not be overwritten by interpretation
- synthesis notes must not contain implicit personal voice
- extracted small notes must not contain implicit personal voice
- personal interpretation belongs in later reflection-style notes, not inside compile products
- if personal interpretation later matures into new knowledge, it should become a new note rather than mutating the original compile note

## 5. Synthesis Note Contract

The synthesis note is the primary compiled output for a raw source.

It acts as:

- the wiki entry point for that source
- the summary of what the source says
- the staging point for later reusable knowledge extraction

### 5.1 Required frontmatter

```yaml
---
id:
title:
layer: wiki
note_type: synthesis
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
confidence:
last_compiled_at:
last_reviewed_at:
raw_bundle_ref:
compiled_from:
---
```

### 5.2 Required body structure

```md
# Title

## Source Summary

## Key Points

## Reusable Ideas

## Candidate Links

## Open Questions

## Source Lineage
```

### 5.3 Section semantics

#### `Source Summary`

Describes what the source is mainly about.

#### `Key Points`

Captures the important source-grounded claims, takeaways, or structural points.

#### `Reusable Ideas`

Extracts the most reusable conceptual or framework-level material while remaining traceable to the source.

#### `Candidate Links`

Records suggested links to other knowledge areas or notes.

These are candidates, not established facts.

#### `Open Questions`

Preserves the unresolved or high-value questions raised by the source.

#### `Source Lineage`

Explicitly records the raw bundle and content lineage.

## 6. Small Note Extraction Rules

Small notes exist to capture high-value reusable knowledge objects, not to slice source text mechanically.

The extraction principle is:

`few and strong, never fragmented for its own sake`

### 6.1 `concept`

Create a concept note only when:

- the source introduces or clarifies a distinct knowledge concept
- the concept can stand on its own
- the concept is likely to recur across multiple future contexts
- the concept is worth linking from other notes

Do not create a concept note when:

- the term is only local to one article
- the idea is too thin to stand independently
- it is only a section label or wording convenience

### 6.2 `framework`

Create a framework note only when:

- the source presents a reusable method, structure, taxonomy, or process
- the structure can be applied beyond the source itself
- the value is in the pattern, not only in the original example

Do not create a framework note when:

- the structure is only article-local
- the pattern is too weak or incomplete
- it is merely a list, not a reusable framework

### 6.3 `question`

Create a question note only when:

- the question is high-value and durable
- it is worth revisiting across multiple future sources
- it can become an inquiry node in the system

Do not create a question note when:

- it is rhetorical
- it is only transitional writing
- it is too narrow to matter beyond the source

### 6.4 `reference`

Use reference notes sparingly.

Create them only when a stable external entity is likely to be cited repeatedly, such as:

- a person
- a company
- a paper
- a book
- a model
- a tool

### 6.5 Quantity rule

Per raw bundle, the first implementation should allow:

- `1` required synthesis note
- `0-3` optional small notes

## 7. Extraction Eligibility Test

A smaller note should be extracted only if it satisfies all of these:

- it can be named independently
- it can be reused across future contexts
- it can plausibly be linked by other notes later
- it does not depend entirely on the original article context to make sense

If any of these fail, the content should remain inside the synthesis note.

## 8. Compile Pipeline

The formal compile pipeline is:

`raw bundle -> validation -> synthesis generation -> small note selection -> wiki write -> link and lineage write-back -> index update`

### 8.1 Raw bundle validation

Before compiling, the system should verify:

- `content.md` exists
- `metadata.md` exists
- `primary_domain` exists
- `conversion_status` is not `failed`
- `review_required` is visible to the compile process

If the bundle requires review, the compiler may still proceed, but the compiled output should reflect that lowered confidence.

### 8.2 Synthesis generation

The compiler must generate exactly one synthesis note per bundle.

### 8.3 Small note selection

The compiler should evaluate whether any concepts, frameworks, questions, or references deserve extraction.

This is a selective elevation step, not a slicing step.

### 8.4 Wiki write

Compiled notes should normally be written into:

- `30_Wiki/<primary-domain>/`

The first implementation should bias toward the primary domain rather than aggressively using `30_Wiki/shared/`.

### 8.5 Link and lineage write-back

The compiler must preserve at least:

- raw bundle -> synthesis note
- synthesis note -> raw bundle
- small note -> raw bundle
- small note -> synthesis note

### 8.6 Index update

The compile result should become discoverable from the relevant domain entry point.

The first implementation may use a simple "recently compiled" style section rather than a complex dynamic indexing system.

## 9. Compile Status And Recompile Rules

The system must avoid uncontrolled note duplication across repeated compile runs.

The compile state should track:

- whether the bundle has been compiled
- which notes were produced
- when the last compile happened

The first implementation may handle this minimally by recording:

- `compiled_at`
- `compiled_note_refs`

Recompile behavior should prefer updating the same compile outputs rather than creating parallel duplicates.

## 10. Confidence Rules

Confidence in compile output should derive in part from raw bundle quality.

Guidance:

- clean text and markdown raw bundles can usually produce higher-confidence synthesis
- HTML or article extraction should usually produce medium confidence unless very clean
- PDF and DOCX imports should generally produce medium confidence by default
- bundles marked `review_required: true` should not silently appear as high-confidence knowledge

## 11. Daily Usage Model

The intended user experience is:

1. import a source into a raw bundle
2. decide whether that source deserves promotion into knowledge
3. compile it into a synthesis note
4. optionally review a few extracted reusable notes
5. read the compiled knowledge instead of repeatedly returning to the raw source
6. later add personal interpretation in separate reflection-style notes
7. use compiled knowledge and later reflections to support outputs

This gives the user a flow of:

`import -> compile -> read -> interpret -> create`

Instead of:

`read raw source -> think from scratch -> write from scratch`

## 12. What Compile Does Not Do

The compile subsystem must not:

- generate user opinion and present it as knowledge
- overwrite raw source bundles
- overwrite synthesis notes with personal interpretation
- create many weak notes from one source just because it can
- treat candidate links as confirmed relationships

## 13. Summary

The wiki compile subsystem is a knowledge compiler, not a generic summarizer and not an opinion generator.

Its job is to convert raw bundles into source-grounded synthesis notes plus a small number of strong reusable knowledge notes, while preserving clean lineage and protecting the wiki layer from interpretation drift.
