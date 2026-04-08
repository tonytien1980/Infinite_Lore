# Reflection And Feedback Specification

**Status:** Draft v1 approved for implementation baseline  
**Date:** 2026-04-09  
**Project:** Infinite Lore

## 1. Purpose

This subsystem defines how `Infinite Lore` accepts user feedback and personal interpretation after an Ask interaction.

Its purpose is to let the user improve the system during real use without polluting source-grounded wiki knowledge.

It must support immediate in-context use rather than deferred cleanup.

## 2. Product Role

The Reflection / Feedback layer exists to:

- capture corrections to existing knowledge safely
- capture the user's own interpretation without mixing it into source-grounded wiki notes
- let later Ask responses benefit from the user's prior reflections
- preserve traceability back to the Ask context and the linked wiki notes

It is not:

- a separate journaling product
- a hidden auto-editing system
- a shortcut that silently rewrites source-grounded notes

## 3. Core Principle

This subsystem must preserve a clean boundary between:

- `source-grounded knowledge`
- `personal interpretation`
- `proposed corrections`

Three core rules:

1. `Corrections must be reviewed before they modify wiki notes.`
2. `Personal interpretation must not be stored as source-grounded wiki content.`
3. `User feedback should influence future Ask results, but by explicit layering, not silent merging.`

## 4. Interaction Model

Reflection / Feedback is integrated directly into the Ask page.

It must not require:

- a separate page
- a modal workflow
- a later cleanup pass

The approved interaction model is:

- one shared feedback input
- two explicit actions:
  - `Correct this knowledge`
  - `Add my interpretation`

This keeps the input simple while preserving different downstream data handling.

## 5. Two Feedback Paths

### 5.1 Correction Path

When the user chooses `Correct this knowledge`:

1. the user enters a correction request
2. the system generates a full proposed corrected version of the target note
3. the user can edit that proposed version inline on the same Ask page
4. the user confirms or rejects the proposal
5. only after confirmation is the target wiki note updated

This path must never silently modify the wiki.

### 5.2 Interpretation Path

When the user chooses `Add my interpretation`:

1. the user enters personal understanding or reaction
2. the system generates a cleaned-up reflection draft
3. the user's raw input is also preserved
4. the user confirms the reflection draft
5. the system stores it as a linked reflection entry

This path does not directly change source-grounded wiki content.

## 6. Ask-Integrated UX

The Ask page should show three major sections:

### 6.1 `Library Answer`

The source-grounded answer layer.

This answer is based on compiled wiki notes and remains the formal knowledge answer.

### 6.2 `Your Reflections`

The user's interpretation layer.

This section should:

- show the most recent `3` relevant reflection entries
- provide a `View all` control
- remain visually separate from the library answer

### 6.3 `Respond Now`

The in-place feedback area.

This area contains:

- one shared input
- the two explicit actions:
  - `Correct this knowledge`
  - `Add my interpretation`

## 7. Link Targeting Rule

Reflection entries should not be attached to a vague Ask session only.

They should attach primarily to the most relevant wiki note used in the Ask answer.

Approved rule:

- if the Ask answer used multiple grounding notes
- the system automatically selects the most relevant note as the primary link target
- the user is not asked to pick one during the initial quick flow

Ask context metadata should still be preserved, but the main attachment point is the wiki note.

## 8. Reflection Entry Behavior

Each interpretation is stored as an independent reflection entry.

The system should not keep appending everything into one growing reflection note by default.

This preserves:

- time-based thought evolution
- separate interpretation moments
- clearer future promotion into higher-order knowledge if needed

## 9. Storage Model

The Reflection / Feedback layer should live inside `50_Brainstorming/`, not as a new canonical top-level knowledge layer.

Recommended structure:

```text
50_Brainstorming/
├── reflections/
│   └── <domain>/
├── corrections/
│   ├── pending/
│   │   └── <domain>/
│   ├── applied/
│   │   └── <domain>/
│   └── rejected/
│       └── <domain>/
```

This reflects that:

- reflections are preserved personal thinking
- correction proposals are governance objects
- neither should be treated as canonical wiki by default

## 10. Reflection Entry Contract

Each reflection entry should contain at least:

```yaml
---
id:
title:
layer: brainstorming
note_type: reflection-entry
primary_domain:
related_domains: []
privacy: private
status: active
created_at:
updated_at:

linked_note_ref:
linked_note_title:
ask_question:
ask_mode:
grounding_note_refs: []
source_refs: []

reflection_kind: interpretation
raw_input:
---
```

Recommended body structure:

```md
# Reflection

## Triggering Question

## My Interpretation

## Linked Context
```

This contract must preserve:

- the Ask context
- the linked wiki note
- the grounding/source lineage
- the original user input

## 11. Correction Proposal Contract

Each correction proposal should contain at least:

```yaml
---
id:
title:
layer: brainstorming
note_type: correction-proposal
primary_domain:
related_domains: []
privacy: private
status: pending
created_at:
updated_at:

target_note_ref:
target_note_title:
ask_question:
ask_mode:
grounding_note_refs: []
source_refs: []

proposal_status: pending
proposal_kind: correction
archive_version_ref:
applied_at:
---
```

Recommended body structure:

```md
# Correction Proposal

## Triggering Question

## Reported Issue

## Proposed Change

## Evidence

## Decision
```

Correction proposals are governance records, not direct hidden edits.

## 12. Correction Review Flow

The approved correction flow is:

1. generate a full corrected version
2. let the user edit that proposal inline on the Ask page
3. require explicit confirmation before applying
4. preserve the previous wiki version before applying
5. refresh the current Ask answer after the change is applied

This makes the system feel immediate without sacrificing knowledge hygiene.

## 13. Versioning And Archive Rule

When a correction is applied:

1. the current wiki note must be archived first
2. the confirmed corrected version becomes the new live wiki note
3. the correction proposal is moved from `pending` to `applied`

Archived versions should be stored under:

```text
80_Archive/wiki-versions/<domain>/
```

Recommended archive filename:

```text
<note-slug>--before-correction--YYYYMMDD-HHMMSS.md
```

This creates lightweight rollback readiness without introducing a heavy version-control UI layer inside the product.

## 14. Ask Behavior After Feedback

### 14.1 After Correction

When a correction is applied:

- the current Ask answer should immediately refresh
- the refreshed answer should reflect the updated source-grounded wiki note

### 14.2 After Interpretation

When a reflection entry is stored:

- it appears in `Your Reflections`
- it does not merge into `Library Answer`
- it becomes available to future Ask responses as a separate personal layer

## 15. Future Ask Layering

Future Ask responses should use both:

- `Library Answer`
- `Your Reflections`

But they must remain visually separated.

Recommended default presentation order:

1. `Library Answer`
2. `Your Reflections`

This ensures:

- user feedback has practical downstream value
- personal interpretation influences future use
- source-grounded knowledge stays visibly distinct

## 16. Non-Goals For The Handy Version

The first handy version should explicitly avoid:

- auto-promoting reflections into canonical knowledge
- hidden silent wiki rewrites
- forcing the user into a second review workspace
- complex restore UI for archived versions
- a separate reflection product or page system

## 17. Definition Of Done

This phase is complete when:

- the Ask page can accept both correction and interpretation actions inline
- correction proposals are review-first, not auto-applied
- interpretations are stored as linked reflection entries
- Ask answers refresh immediately after an applied correction
- Ask responses show reflections as a separate layer
- archived pre-correction wiki versions are preserved
- the workflow remains simple enough to complete in the same Ask context
