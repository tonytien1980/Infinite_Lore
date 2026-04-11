# Raw Enrichment And Multi-Provider Routing Specification

**Status:** Approved for implementation
**Date:** 2026-04-11  
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next capability layer after the delivered macOS app shell polish baseline.

Its purpose is to make `Infinite Lore` behave more like a real personal `LLM Wiki` by adding:

- model-backed understanding of newly imported raw material
- clearer provider and model-role routing
- a stable architecture that supports both cloud and local models

This phase is not about changing the core identity of the product.

It is about making the existing pipeline:

`scan -> raw -> compile -> ask`

smarter at the right places, without letting model cost or model volatility contaminate raw preservation.

## 2. Product Role

This phase exists to answer three product needs at once:

1. newly captured raw material should be understood and classified automatically
2. `Ask` should continue to use the strongest answer path available
3. provider architecture should stop being locked to a single cloud-only implementation

The resulting system should feel like:

- a local-first knowledge workflow
- cloud-accelerated where quality matters most
- source-preserving at the raw layer
- provider-flexible without becoming a model control panel

It should not feel like:

- every step is an expensive model call
- every screen is asking the user to pick a model manually
- the raw intake path can fail just because one provider is temporarily unavailable

## 3. Core Principle

The system must separate:

- `raw capture`
- `raw understanding`
- `wiki compilation`
- `answer generation`

These are not the same job.

The key principle for this phase is:

`Preserve first. Understand second. Answer with the best available route.`

Three hard rules:

1. Raw source capture must remain deterministic and source-preserving.
2. Search, RSS, and website scanning must not depend on model calls.
3. Model-backed enrichment or answering must never be allowed to destroy or block raw preservation.

## 4. Why This Phase Comes Next

The current product already supports:

- practical source scanning
- raw import
- wiki compile
- grounded Ask
- reflection / correction
- multimodal ingest
- desktop shell

But the current model architecture is still limited:

- `Ask` is the only delivered model-backed path
- backend routing currently only resolves `openai`
- settings UI currently behaves as if one provider is the default live path
- raw import currently preserves and compiles material, but does not add a dedicated model-backed understanding layer between raw intake and later use

This means the next highest-value improvement is not another UI pass first.

It is to define:

- where model cost should be spent
- where model cost should not be spent
- how OpenAI and local providers should coexist
- how raw understanding should improve without weakening the raw contract

## 5. Scope Of This Phase

This phase defines two connected capabilities:

### 5.1 Raw Enrichment

A new background understanding layer for imported raw bundles.

### 5.2 Multi-Provider Routing

A route-driven provider architecture that supports:

- `OpenAI`
- `Ollama`
- future local provider expansion

This phase does **not** include:

- full unrestricted web search through model tool use
- replacing current deterministic scanning logic with model inference
- turning query into an internet search feature
- a graph UI
- full local-model orchestration across every existing route on day one

## 6. The Raw Pipeline After This Phase

After this phase, the conceptual pipeline becomes:

`scan/search capture -> raw normalization -> raw enrichment -> compile -> ask`

These stages have different responsibilities.

### 6.1 Raw normalization

This is deterministic, model-free, and mandatory.

It includes:

- source fetch
- article extraction
- OCR where applicable
- canonical URL detection
- content hashing
- author / title / date extraction where possible
- bundle creation
- bundle metadata persistence

### 6.2 Raw enrichment

This is model-backed, background, and retryable.

It includes:

- domain suggestion
- related-domain suggestion
- short semantic summary
- topic / entity hints
- value and quality flags
- wiki update hints

### 6.3 Compile

Compile remains the source-grounded knowledge compiler.

This phase does not turn compile into a free-form summarization system.

Instead, compile may later read the enrichment sidecar as advisory input while preserving:

- one raw bundle per source capture
- one synthesis note per source
- merge-first smaller note behavior
- source-grounded note lineage

## 7. Search And Scan Boundary

The user explicitly wants:

- RSS support
- website scanning
- article-list capture
- database-like source collection behavior

This phase keeps that search layer model-free by default.

Approved rule:

`Search finds. Models understand.`

This means:

### 7.1 Search / scan uses no model

- RSS polling
- website scanning
- article-list extraction
- deduplication
- raw fetch and normalization

These stay in the current deterministic pipeline.

Reason:

- OpenAI shared free token pools do not cover search/tool-use costs the same way
- search is high-frequency and mechanically repeatable
- this work is cheaper and more reliable without model dependence

### 7.2 Models operate after capture

Once content is already inside a raw bundle, model-backed work can begin.

This preserves:

- cost control
- raw reproducibility
- better failure isolation

## 8. Raw Enrichment Behavior

The user chose:

- `default all automatic`
- background execution
- raw import must still succeed if enrichment fails

So the approved enrichment behavior is:

### 8.1 Trigger model

When a raw bundle is successfully created:

1. the raw bundle is immediately preserved
2. the bundle is marked `enrichment_pending`
3. a background enrichment job is queued
4. the user does not need to press another button

### 8.2 Execution posture

Raw enrichment should run:

- automatically
- in the background
- without blocking `Scan now`
- without blocking bundle preservation

### 8.3 Failure posture

If enrichment fails:

- raw bundle remains valid
- bundle state records the failure
- the system may retry later
- compile must not be treated as globally broken just because enrichment failed

The approved behavior is:

`raw first, enrichment eventually`

## 9. Enrichment Output Contract

The first version should write a bundle-local enrichment artifact rather than silently mutating raw source content.

Recommended location:

- bundle sidecar file inside the raw bundle directory

Recommended filename:

- `enrichment.json`

### 9.1 Required fields

The first version should record at least:

```json
{
  "status": "pending | completed | failed | retry_scheduled",
  "provider": "openai | ollama | unknown",
  "model": "gpt-5.4-mini",
  "started_at": "2026-04-11T00:00:00Z",
  "completed_at": "2026-04-11T00:00:00Z",
  "failure_reason": "",
  "primary_domain_suggestion": "ai-application",
  "related_domains_suggestion": ["management"],
  "summary": "Short bounded summary.",
  "topic_tags": ["knowledge-management", "llm-wiki"],
  "entity_hints": ["Andrej Karpathy", "Graphify"],
  "quality_flags": ["high-signal", "review-required"],
  "wiki_update_hint": "new-synthesis | strengthen-existing-domain | possible-rewrite-candidate"
}
```

### 9.2 Boundary rule

This enrichment artifact is:

- advisory
- replaceable
- recomputable

It is not:

- the raw source
- the canonical wiki
- the user's reflection

## 10. Provider Architecture

This phase should move the system from:

- one real provider path

to:

- one provider abstraction layer with multiple provider slots

### 10.1 Supported providers in the architecture

The architecture should support:

- `openai`
- `ollama`

Future-compatible but out of first implementation scope:

- `llama.cpp server`
- other OpenAI-compatible local or hosted providers

### 10.2 First operational default

Even though the architecture is multi-provider, the user explicitly chose:

- `OpenAI` as the only active first model source
- because of the daily free token pool from the data-sharing program

So the first operational default is:

`OpenAI shared-first`

### 10.3 Why still design multi-provider now

Because the user also explicitly wants the system to become local-capable later without rewriting the whole routing layer.

So the architecture must be written now to support:

- cloud-first today
- hybrid later
- local-heavy later if desired

## 11. Role And Route Model

The system already has route concepts such as:

- `scan`
- `import`
- `compile`
- `query`
- `ask`
- `reflection`

This phase should preserve route-based control, but refine how routes map to model-backed work.

### 11.1 Approved role model

Keep the existing high-level role language:

- `no_model`
- `balanced`
- `best_deep`

### 11.2 New route interpretation

The route strategy after this phase should be:

- `scan`: `no_model`
- `import`: deterministic raw normalization only
- `enrich_raw`: `balanced`
- `compile`: local-first or model-optional later
- `query`: `no_model`
- `ask`: `best_deep`
- `reflection`: `balanced`

This means the system should add an explicit new route:

- `enrich_raw`

instead of overloading the old `import` route with two different jobs.

## 12. Default Provider Strategy

The user approved this default task split:

- `Ask`: OpenAI priority
- `raw enrichment`: OpenAI priority
- `compile / large-page rewriting`: local priority
- `query / scan / RSS / website capture`: no model

### 12.1 First default mapping

For the first version, the recommended mapping is:

- `balanced` on OpenAI:
  - `gpt-5.4-mini`
- `best_deep` on OpenAI:
  - `gpt-5.4`

And the local provider slots should be structurally present for later:

- `balanced` on Ollama:
  - future `Qwen`
- `best_deep` or `rewrite`-style heavy work on Ollama:
  - future `Gemma`

### 12.2 Operational default

If no local provider is configured:

- the system should simply run on OpenAI
- it should not require a local model to be present

If a local provider is configured later:

- the system may selectively route local-first tasks to that provider

## 13. OpenAI Shared-First Policy

Because the user participates in the OpenAI API data-sharing incentive program and explicitly accepts shared usage, this phase does **not** add a separate privacy-mode branch.

The system therefore assumes:

- OpenAI may be the default high-value path
- shared token pools are intentionally used where they create the most product value

That value should be spent on:

- `Ask`
- raw understanding and classification
- higher-quality synthesis-style responses

It should not be spent on:

- RSS fetch
- web scanning
- dedup
- mechanical import normalization

## 14. Local Provider Architecture

Even though OpenAI is the first active default, the local provider path must be defined now.

### 14.1 Ollama assumptions

The first local provider contract should assume:

- OpenAI-compatible style request mapping where feasible
- configurable local base URL
- no API key by default
- model IDs such as local `Qwen` or `Gemma`

### 14.2 Why compile is local-priority later

Large-scale page rewriting, bundle consolidation, and heavy wiki update work are:

- expensive
- repeatable
- often batch-oriented

These are the most natural later workloads for local models.

So the architecture should anticipate:

- OpenAI for high-value interactive quality
- local models for high-volume wiki maintenance

## 15. Settings UX Direction

The product should not become a visible model cockpit.

The settings page should support multiple providers, but the homepage should remain simple.

### 15.1 Settings responsibilities

The settings surface should support:

- multiple provider entries
- provider type
- provider connection fields
- model ID by role
- route-to-role mapping
- route-to-provider preference where needed

### 15.2 Homepage responsibilities

The homepage should remain:

- `Ask-first`
- low-friction
- not full of model toggles

At most, a lightweight override may exist later.

But the normal product posture should be:

`route automatically based on system rules`

## 16. State And Failure Model

This phase should add explicit state handling for enrichment work.

### 16.1 Bundle enrichment states

- `pending`
- `running`
- `completed`
- `failed`
- `retry_scheduled`

### 16.2 Failure handling

If OpenAI is unavailable or returns an error:

- raw bundle remains intact
- enrichment state becomes `failed` or `retry_scheduled`
- compile and Ask continue using what is already available

The system must never behave as if:

- one provider outage destroyed the user's library

## 17. Compile Relationship

The first implementation should not make compile depend hard on enrichment success.

Recommended first posture:

- raw normalization writes the bundle
- compile may still proceed using current deterministic rules
- enrichment updates sidecar understanding in the background
- later compile or recompile may optionally use enrichment as advisory input

This avoids turning the whole product into:

- `no enrichment, no knowledge`

That would be too brittle for a first model-enrichment phase.

## 18. Ask Relationship

`Ask` remains the clearest place to spend high-quality cloud model budget.

The current grounded answer model should remain:

1. retrieve from wiki
2. gather trace and relation evidence
3. answer from grounded notes only

What changes in this phase is:

- the answer path becomes explicitly provider-routed
- OpenAI shared-first becomes the normal default

## 19. First Implementation Boundaries

The first implementation of this phase should include:

- multi-provider config structure
- OpenAI shared-first operational default
- explicit `enrich_raw` route
- background raw enrichment queue / state model
- enrichment sidecar artifact
- OpenAI-backed raw enrichment
- settings and route UX for the above

The first implementation should **not** require:

- local provider execution for every route
- full compile rewrite logic through local models
- privacy-mode branching
- multi-provider UI clutter on the homepage

## 20. Definition Of Done

This phase is done when:

- raw capture remains deterministic and model-free
- raw enrichment runs automatically in the background
- enrichment failure does not block raw preservation
- OpenAI is the real default model path for `Ask` and `enrich_raw`
- the architecture supports local providers without requiring them immediately
- the settings layer can represent more than one provider cleanly
- the user does not need to manually choose a provider every time they use the system

## 21. Next Step After This Phase

Once this spec is approved, the next step should be:

- implementation planning for `raw enrichment + multi-provider routing`

That plan should break the work into at least:

1. provider config schema and backend routing changes
2. settings UI changes
3. raw enrichment queue and state model
4. OpenAI shared-first enrichment implementation
5. later local-provider execution slices
