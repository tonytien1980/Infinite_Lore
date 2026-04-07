# Infinite Lore System Specification

**Status:** Draft v1 approved for implementation baseline  
**Date:** 2026-04-07  
**Project:** Infinite Lore

## 1. Product Definition

`Infinite Lore` is an Obsidian-native, AI-maintained personal context system for a single primary user.

Its purpose is to turn raw source material, structured knowledge, exploratory thinking, work context, and writing outputs into one local-first operating system for knowledge and creation.

It is not:

- another chat app
- a replacement for Obsidian
- a multi-user SaaS product
- a custom UI shell built before the underlying system exists

It is:

- a local-file-first vault system
- a durable information architecture
- a set of workflows that both Obsidian and external AI agents can operate on
- a writing and knowledge environment that can evolve over time without losing history

## 2. Core Goal

The system must support a stable production chain across the following activities:

- collect raw materials
- compile raw materials into reusable knowledge
- explore ideas, comparisons, questions, and writing directions
- support active work and client-related projects
- produce artifacts such as social posts, consulting content, research notes, course materials, and book drafts
- optionally accept journal-style personal input, without requiring journaling as a prerequisite for the rest of the system

The primary operating direction is:

`knowledge-first, journal-optional, writing-enabled`

## 3. Architectural Decision

The approved architecture is:

`Obsidian-native + lightweight orchestration layer`

This means:

- Obsidian is the main environment for reading, browsing, linking, search, and manual editing
- external AI agents such as Codex or Claude can operate directly on the same vault
- the system must remain usable even without a custom frontend
- all critical value must live in the vault structure, note contracts, metadata, and workflows

## 4. System Principles

- `raw` is the preserved source-of-truth layer and is not rewritten by the system
- `wiki` is the maintained knowledge layer and can evolve over time
- `brainstorming` is an exploration layer and is not automatically treated as canonical knowledge
- `projects` is the active work layer for ongoing execution
- `journal` is a valid formal input layer, but not a required one
- `artifacts` is the output layer and must remain traceable to upstream knowledge and source material
- storage is organized by system role first
- daily reading and navigation are organized by domain first
- every formal note must have one `primary_domain`
- notes may also have multiple `related_domains`
- domain structure must remain evolvable over time
- preserve first, then refine
- traceability is more important than surface elegance

## 5. Core Layers

The system formally includes six major layers.

### 5.1 `raw`

The raw source layer.

Examples:

- articles
- PDFs
- book excerpts
- web captures
- transcripts
- images with extracted notes

Rules:

- raw content is not rewritten in place
- files are retained by default
- AI may add adjacent metadata, but not modify the original source body

### 5.2 `wiki`

The maintained knowledge layer.

This layer contains:

- concepts
- frameworks
- syntheses
- references
- question notes
- theme maps

Rules:

- wiki notes should be knowledge objects, not raw summaries pasted into a new file
- every wiki note should trace back to source material or other upstream reasoning
- wiki notes may evolve, but must retain lineage

### 5.3 `projects`

The active work layer.

This layer contains:

- consulting projects
- content projects
- research efforts
- focused topic initiatives

Rules:

- projects hold active state, decisions, next steps, and work logs
- projects are not interchangeable with wiki notes

### 5.4 `brainstorming`

The exploratory reasoning layer.

This layer contains:

- writing ideation
- topic comparisons
- argument exploration
- scope analysis
- contradiction checks
- pre-output thinking

Rules:

- brainstorming is preserved, but is not automatically elevated to wiki
- durable insights may later be promoted into wiki, projects, or artifacts

### 5.5 `journal`

The personal input layer.

This layer contains:

- free writing
- energy and mood notes
- life reflection
- personal themes over time

Rules:

- journal is a valid system entry point
- journal is not mandatory for the rest of the system to function
- journal originals should behave as append-only records

### 5.6 `artifacts`

The output layer.

This layer contains:

- social content
- consulting deliverables
- research outputs
- course materials
- book drafts

Rules:

- artifacts should reference upstream knowledge and thinking where practical
- outputs must remain distinguishable from source and knowledge layers

## 6. Domain Model

Navigation and everyday reading should be domain-first.

Initial top-level domains:

- business-strategy
- management
- marketing-acquisition
- finance-investing
- ai-application
- consulting
- personal

Domain rules:

- every formal note must declare a `primary_domain`
- every note may declare multiple `related_domains`
- domains can be added later
- domains can be split, merged, or renamed
- display names may evolve, but stable identifiers should remain consistent
- cross-domain material should be linked through metadata and references rather than duplicated in full

## 7. Storage Model

Storage is organized by system role first. Reading is organized by domain first.

This means:

- the vault structure separates `raw`, `wiki`, `projects`, `brainstorming`, `journal`, and `artifacts`
- the main user experience is not meant to be browsing raw folders directly all day
- domain index notes act as the primary operating entry points for day-to-day use

## 8. Proposed Vault Structure

```text
Infinite Lore/
├── 00_System/
│   ├── Home.md
│   ├── Domain Map.md
│   ├── Operating Principles.md
│   ├── Schema.md
│   ├── Workflow Guide.md
│   └── Health Rules.md
├── 10_Domains/
│   ├── business-strategy/index.md
│   ├── management/index.md
│   ├── marketing-acquisition/index.md
│   ├── finance-investing/index.md
│   ├── ai-application/index.md
│   ├── consulting/index.md
│   └── personal/index.md
├── 20_Raw/
│   ├── inbox/
│   └── done/
│       ├── business-strategy/
│       ├── management/
│       ├── marketing-acquisition/
│       ├── finance-investing/
│       ├── ai-application/
│       ├── consulting/
│       └── personal/
├── 30_Wiki/
│   ├── business-strategy/
│   ├── management/
│   ├── marketing-acquisition/
│   ├── finance-investing/
│   ├── ai-application/
│   ├── consulting/
│   ├── personal/
│   └── shared/
├── 40_Projects/
│   ├── active/
│   ├── paused/
│   ├── completed/
│   └── clients/
├── 50_Brainstorming/
│   ├── by-domain/
│   ├── by-project/
│   ├── by-artifact/
│   └── sessions/
├── 60_Journal/
│   ├── daily/
│   ├── weekly/
│   └── life-themes/
├── 70_Artifacts/
│   ├── social/
│   ├── consulting/
│   ├── research/
│   ├── courses/
│   └── books/
├── 80_Archive/
└── 90_Assets/
```

## 9. Navigation Model

`Infinite Lore` does not require a custom homepage UI. All "home" and "dashboard" concepts are implemented as Obsidian notes.

The formal navigation model includes:

- `00_System/Home.md` as the vault-wide home note
- `10_Domains/<domain>/index.md` as the primary domain entry note
- specialized index notes for projects, outputs, reviews, and theme maps

Each domain index should contain two areas.

### 9.1 Fixed navigation area

- core concept links
- key index links
- representative notes
- recent outputs
- main related projects

### 9.2 Dynamic work area

- recent raw inputs
- topics waiting to be processed
- writing opportunities
- cross-domain connections
- recent activity

## 10. Raw Contract

The `raw` layer follows these rules:

- original source files are not rewritten
- AI may add metadata in an adjacent note or sidecar file
- `20_Raw/inbox/` receives new materials
- processed materials move to `20_Raw/done/`
- old raw materials are retained by default
- deletion is an exceptional maintenance action, not a daily workflow

Each raw item should consist of:

- the original source file or imported text note
- one adjacent manifest note or metadata note

Minimum raw metadata:

```yaml
source_type:
source_title:
source_ref:
imported_at:
source_created_at:
published_at:
primary_domain:
related_domains: []
privacy:
content_hash:
status:
```

## 11. Wiki Contract

The `wiki` layer stores maintained knowledge, not just processed excerpts.

Supported wiki note types:

- concept
- framework
- question
- synthesis
- reference
- theme-map

Minimum wiki metadata:

```yaml
note_type:
primary_domain:
related_domains: []
source_refs: []
confidence:
status:
last_compiled_at:
last_reviewed_at:
```

Wiki rules:

- prefer concepts and insight units over article rewrites
- retain lineage to `raw` or other upstream reasoning
- allow AI updates without breaking traceability
- allow cross-domain linking without forcing single-domain isolation

## 12. Project Contract

Each project must have at least three core notes:

- `status.md`
- `thinking.md`
- `log.md`

### 12.1 `status.md`

Must capture:

- current state
- objective
- next actions
- risks
- timeline or deadline context
- linked resources

### 12.2 `thinking.md`

Must capture:

- externalized reasoning
- problem decomposition
- open questions
- working hypotheses

### 12.3 `log.md`

Must capture:

- work log entries
- decisions made
- progress updates
- meeting summaries when relevant
- completed items

Optional project notes:

- `brief.md`
- `deliverables.md`
- `references.md`

## 13. Brainstorming Contract

The `brainstorming` layer preserves exploratory reasoning without forcing it into canonical knowledge.

It is used for:

- writing ideation
- problem framing
- outline exploration
- argument comparison
- topic expansion
- gap analysis
- health and contradiction checks

Rules:

- brainstorming notes can remain temporary or exploratory
- they are not automatically canonical
- durable insights can later be promoted elsewhere
- if a note serves only one output, it may remain linked only to an artifact

## 14. Journal Contract

The `journal` layer is a formal input lane, but not a system requirement.

It supports:

- daily free writing
- state tracking such as mood, energy, and sleep
- recurring life themes
- personal thinking that may later feed other layers

Rules:

- journal originals should remain append-only
- AI may create derivative structured notes based on journal entries
- AI should not overwrite original daily writing
- journal content may route into `wiki`, `projects`, `artifacts`, or `life-themes`
- the system must still function for users who do not journal regularly

## 15. Artifact Contract

The `artifacts` layer stores formal outputs.

Initial supported artifact types:

- social
- consulting
- research
- courses
- books

Minimum artifact metadata:

```yaml
artifact_type:
audience:
goal:
source_refs: []
linked_wiki: []
linked_brainstorming: []
stage:
privacy:
```

Recommended artifact stages:

- brief
- outline
- draft
- revised
- final
- published
- delivered

## 16. Metadata Standard

All formal notes should share a common frontmatter core:

```yaml
id:
title:
layer:
note_type:
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
```

Metadata rules:

- `primary_domain` is required
- `related_domains` is optional and multi-valued
- `privacy` must at least support `private`, `publishable`, and `client-confidential`
- `status` must reflect lifecycle state, not only completion

## 17. Client and Privacy Model

The initial privacy model is:

- one main vault
- consulting material lives in the same vault with explicit privacy tiers
- client project material is stored under `40_Projects/clients/`
- consulting outputs are stored under `70_Artifacts/consulting/`
- all confidential client material must use `privacy: client-confidential`
- public-facing writing must not quote confidential client material directly unless transformed into clearly abstracted, non-sensitive insight

This model is chosen because it:

- preserves cross-domain insight potential
- keeps the system unified
- still provides clear separation rules
- allows highly sensitive clients to be split into separate vaults later if needed

## 18. Primary User Flows

### 18.1 Knowledge-first writing

- import article, PDF, book excerpt, or source note into `20_Raw/inbox/`
- process and move it into `20_Raw/done/`
- compile reusable knowledge into `30_Wiki/`
- explore topic direction in `50_Brainstorming/`
- create `70_Artifacts/` outputs such as brief, outline, and draft

### 18.2 Project-first work

- create or reopen a project in `40_Projects/`
- read `status.md`
- think in `thinking.md`
- log progress and decisions in `log.md`
- connect outputs into `70_Artifacts/` as needed

### 18.3 Journal-first reflection

- write in `60_Journal/daily/`
- route useful content into life themes, projects, wiki, or artifacts
- create periodic weekly synthesis in `60_Journal/weekly/`

## 19. Daily Usage Expectation

Normal usage inside Obsidian should feel like this:

- open `00_System/Home.md`
- enter a domain through its `index.md`
- review recent source material, maintained knowledge, open writing directions, related projects, and recent outputs
- begin writing from knowledge and exploratory thinking, not from an empty page
- use journaling only when it helps, not because the system demands it

## 20. AI Operating Rules

Any AI agent operating on the system must follow these rules:

- never rewrite raw source content
- preserve lineage when generating wiki or artifact content
- do not automatically treat brainstorming as canonical wiki
- never overwrite original journal entries
- update related index notes when adding important formal notes
- require `primary_domain` on every formal note
- prefer metadata and linking over content duplication for cross-domain material
- when uncertain, add a new note rather than overwrite an important existing note

## 21. Health and Maintenance

The system should support health checks for at least the following:

- notes missing a domain
- wiki or artifact notes missing source references
- important notes not surfaced by any index
- isolated or stale wiki notes
- confidential notes marked as publishable
- broken raw-to-wiki lineage
- broken wiki-to-artifact lineage

## 22. Initial Formal Scope

The first implementation phase based on this spec should include:

- vault structure creation
- core navigation note creation
- schema and metadata standard definition
- note templates for each layer
- domain index structure
- knowledge-first workflow definition
- project workflow definition
- journal workflow definition
- artifact pipeline definition
- health-check rule definition

Explicitly out of scope for the first implementation phase:

- custom web UI
- direct Google Drive integration
- email integration
- calendar integration
- multi-user permissions
- mobile-specific product layer

## 23. Summary

`Infinite Lore` is not primarily an app. It is an AI-maintained, Obsidian-native personal context system.

Its foundation is stable system layers. Its daily experience is domain-first. It does not require existing journaling habits to be useful. It can begin from curated knowledge and grow into a complete environment for public writing, consulting work, research, and personal context over time.
