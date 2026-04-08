# Query And Ask Specification

**Status:** Draft v1 approved for implementation baseline  
**Date:** 2026-04-08  
**Project:** Infinite Lore

## 1. Purpose

This subsystem defines how `Infinite Lore` answers questions and helps the user find knowledge from the existing vault.

Its purpose is not to behave like a general chat assistant.

Its purpose is to behave like a grounded library manager for the user's own knowledge system.

## 2. Product Role

`Ask` is the primary answer layer.

`Query` is the supporting discovery layer.

They are not separate unrelated tools. They are two response modes inside one knowledge entry surface.

The system should feel like:

- a personal library manager
- answer-first when appropriate
- source-transparent
- grounded in the user’s own vault

The system should not feel like:

- a general internet chatbot
- an open-ended autocomplete machine
- a model that invents answers when the library does not contain the needed material

## 3. Core Principle

The Query/Ask layer must serve the library, not replace it.

Three core rules:

1. `Ask serves the library, not the open internet.`
2. `Ask answers from the vault first.`
3. `If the library does not know, Ask must say so.`

## 4. Interaction Model

The approved interaction model is:

`single input, auto-routed intent, manual override available`

The user should not face two separate chat boxes for Query and Ask.

Instead:

- the user types into one input
- the system infers whether the user wants:
  - retrieval-oriented discovery
  - grounded synthesized answering
- the user may manually override the routing mode when needed

Supported modes:

- `Auto`
- `Ask`
- `Query`

## 5. Query Role

`Query` is responsible for:

- locating relevant notes
- filtering by domain
- showing what already exists
- helping the user explore the knowledge base directly

Typical Query-style prompts include:

- "What notes do I have about X?"
- "Which domain has information about Y?"
- "Show me recent notes related to Z."
- "What synthesis notes exist for this topic?"

Query is:

`knowledge discovery mode`

## 6. Ask Role

`Ask` is responsible for:

- answering from the compiled wiki
- synthesizing relevant knowledge into a usable answer
- keeping the answer grounded and traceable

Typical Ask-style prompts include:

- "What is the current knowledge on X?"
- "Summarize what my system knows about Y."
- "Compare the ideas currently stored about Z."
- "What can I already use to write about this topic?"

Ask is:

`grounded answer mode`

## 7. Auto Mode Routing

Auto mode should infer whether the prompt is primarily Query or Ask.

### 7.1 Query-intent signals

Examples:

- "What notes do I have..."
- "List..."
- "Show..."
- "Which notes..."
- "Find..."

### 7.2 Ask-intent signals

Examples:

- "What is..."
- "Summarize..."
- "Compare..."
- "Explain..."
- "What does my library currently say about..."

### 7.3 Default bias

If intent is ambiguous, Auto mode should bias toward:

`Ask`

Because the user's preferred mode is answer-first interaction.

## 8. Retrieval Strategy

The first retrieval layer should be the compiled wiki, not the raw source layer.

Primary retrieval targets:

- `synthesis`
- `concept`
- `framework`
- `question`

`raw` bundles are the trace layer, not the first answer layer.

This means:

- the system should answer from organized knowledge first
- raw bundles should be used to prove lineage, not to replace compiled knowledge during normal answer generation

## 9. Retrieval Order

The first version should retrieve in this order:

1. relevant synthesis notes
2. relevant smaller notes
3. raw lineage only for trace display

The answer should be shaped primarily by:

- synthesis notes first
- then reinforced by smaller reusable notes

## 10. Retrieval Scope Control

The system must not throw the whole vault into every answer request.

The first version should keep retrieval narrow and controlled.

Recommended scope:

- `3-5` most relevant synthesis notes
- `0-5` supporting smaller notes

This keeps:

- cost controlled
- answer focus high
- hallucination pressure lower

## 11. Ask Output Structure

Every Ask response should contain these layers:

### 11.1 `Answer`

The direct organized answer.

### 11.2 `Grounding`

A structured list of the wiki notes that shaped the answer.

This should reference:

- synthesis notes
- relevant smaller notes

### 11.3 `Trace to Source`

A way to trace the answer back to:

- raw bundles
- source files

### 11.4 `Limits`

A visible section or signal showing when:

- evidence is incomplete
- the system is making a limited inference
- the library does not currently contain enough information

## 12. Ask Safety Mode

The default Ask mode must be:

`strict grounded mode`

This means:

- answers are based on existing wiki knowledge
- insufficient evidence results in partial or refused answers
- silent invention is forbidden
- any inference must be marked as inference
- personal reflection notes must not silently appear as source-grounded facts

## 13. Evidence Handling

The answer pipeline must support three evidence states.

### 13.1 Sufficient evidence

The system can provide a full grounded answer.

### 13.2 Partial evidence

The system should answer only the grounded portion and clearly state what remains uncertain.

### 13.3 Insufficient evidence

The system should explicitly state that the current library does not contain enough evidence to answer confidently.

It may still show:

- related notes
- relevant bundles
- likely next sources to inspect

## 14. Cost Control Strategy

The user wants a cost-aware system.

The first version should therefore follow this rule:

`control cost through disciplined retrieval`

### 14.1 No-model steps

These should stay local when possible:

- scan
- raw intake monitoring
- bundle management
- health checks
- basic query listing

### 14.2 Model-justified step

The most justified place to spend model cost is:

- grounded answer synthesis

This means:

- retrieve locally first
- synthesize with a model second

### 14.3 Query cost rule

Query mode should prefer:

- local retrieval only
- no model by default

### 14.4 Ask cost rule

Ask mode may use a configured model, but only after the candidate note set has been narrowed.

## 15. Model Routing

The Query/Ask layer must respect the Workbench routing system.

The role system remains user-controlled, not system-guessed.

Expected defaults:

- Query -> `no_model`
- Ask -> `best_deep`

Optional later override:

- some Ask requests may use `balanced`

But the first version should not attempt complex dynamic cost optimization.

## 16. Relationship To Reflections

The Query/Ask layer must respect the boundary between:

- source-grounded wiki knowledge
- personal reflections

The first version should not silently mix reflection notes into grounded answers.

If reflection support is added later, it should be:

- explicitly labeled
- clearly separated from source-grounded evidence

## 17. What This Subsystem Is Not

The first Query/Ask layer is not:

- a general web-aware assistant
- a reflection-writing agent
- an autonomous multi-step researcher
- a vault-rewriting agent

It is:

- a grounded answer and discovery layer over the user’s current library

## 18. First-Version Scope

The first implementation should include:

- single input with mode selector
- auto Ask/Query routing
- local retrieval over existing wiki notes
- grounded Ask responses
- grounding display
- raw lineage trace display
- explicit limits when evidence is weak

It should not yet include:

- open-internet augmentation by default
- heavy semantic reranking systems
- long-running autonomous reasoning loops
- automatic reflection integration into grounded answers

## 19. Summary

The Query/Ask subsystem is the answering surface of Infinite Lore.

Its job is to behave like a grounded library manager over the user's own vault: help find notes when discovery is needed, synthesize answers when explanation is needed, stay transparent about sources, and refuse to invent knowledge the library does not actually contain.
