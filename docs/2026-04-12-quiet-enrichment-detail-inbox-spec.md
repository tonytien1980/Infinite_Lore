# Quiet Enrichment Detail In Inbox

**Status:** Draft for review
**Date:** 2026-04-12  
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next enrichment-operations slice after delivered manual retry / dismiss recovery controls.

Its purpose is to make enrichment more understandable without making the Workbench feel like a queue-management console.

The target is:

- keep `摘要` calm and overview-first
- keep `收件匣` readable at a glance
- let the user understand what enrichment actually produced when they care
- avoid surfacing model-maintenance noise by default

## 2. Why This Comes Next

The current delivered baseline already provides:

- honest enrichment states in `摘要` and `收件匣`
- inline `重試` / `清除` controls for actionable failed / deferred queue entries
- bounded background enrichment while Workbench is open

What is still missing is the user’s ability to answer this simple question:

`這份原始資料到底被整理成了什麼？`

Right now the UI can say:

- pending
- completed
- failed
- deferred

But it still does not quietly show:

- what the enrichment concluded
- which domain it seems to belong to
- what themes or entities were inferred
- why a failed / deferred item ended up in that state

That means the next most valuable improvement is not more queue control.

It is better per-bundle understanding with a low-noise UI posture.

## 3. Recommended Approach

Approved approach:

`quiet preview plus progressive disclosure inside 收件匣 only`

This means:

- `摘要` stays unchanged and overview-first
- `收件匣` adds one lightweight enrichment preview line per bundle row
- a user can expand `查看詳情` inline only when they want more context
- expanded detail focuses on interpretation results and operator-meaningful reasons
- technical routing fields stay hidden from the default surface

Why this is preferred:

- it adds understanding without turning the list into an operations console
- it preserves scan- and import-first workflow speed
- it respects the user’s request that front-end detail should not become distracting
- it can be delivered inside the existing list rather than through a new page

## 4. Core Principle

This phase should follow one UX rule:

`Default calm. Detail on demand.`

Applied more concretely:

1. the default row remains short and scannable
2. a user should learn something meaningful without expanding too often
3. expanded detail should explain the enrichment result, not expose backend plumbing
4. technical fields should appear only when they directly help the user act

## 5. Scope

This phase includes:

### 5.1 Quiet preview in `收件匣`

Each bundle row may show:

- current enrichment status
- one short preview sentence
- a `查看詳情` toggle when richer enrichment detail exists

The preview line should stay single-purpose and compact.

### 5.2 Inline expanded enrichment detail

When expanded, the bundle row may show:

- short enrichment summary
- `primary domain suggestion`
- `related domain suggestions`
- topic tags
- entity hints
- concise status reason for `failed` / `deferred`
- last updated time

### 5.3 Calm failure explanation

For `failed` and `deferred` items, the UI should explain the current state in short operator language.

It should help the user understand:

- whether retry makes sense
- whether the item is simply waiting on a future execution path

## 6. Explicit Non-Goals

This phase does **not** include:

- changing `摘要` into a detail surface
- a dedicated enrichment detail page
- provider or model pickers in the bundle list
- raw JSON inspection in the normal UI
- queue-debug panels
- model telemetry, token usage, or request logs
- bulk expand / collapse controls
- new recovery actions beyond the already delivered `重試` / `清除`

## 7. Information Hierarchy

### 7.1 Default row content

The collapsed row should answer:

- what this bundle is
- whether it is usable or needs attention
- the shortest meaningful enrichment takeaway

Recommended collapsed order:

1. title
2. primary domain or bundle context
3. bundle path / review posture / enrichment status
4. one-line enrichment preview
5. optional `查看詳情`

### 7.2 Expanded detail content

The expanded area should answer:

- what the system thinks this bundle is about
- where it may belong in the knowledge structure
- why it is blocked if it did not complete

Recommended expanded sections:

1. `整理摘要`
2. `建議領域`
3. `主題與實體`
4. `目前狀態說明`
5. `最後更新`

### 7.3 Fields that stay hidden by default

The normal Workbench surface should not foreground:

- provider id
- model id
- queue internals
- sidecar JSON fields verbatim

Those fields are still useful operationally, but they should not become the default reading experience.

## 8. Content Rules

### 8.1 Preview sentence

The preview sentence should be:

- at most one line in the default row
- plain and direct
- interpretation-focused rather than system-focused

Good examples of the intended posture:

- `這份資料主要在談 AI 工作流整理與知識維護。`
- `目前已整理出明確的行銷主題與受眾線索。`
- `這份資料暫時延後，因為目前尚未有可執行的增補路由。`

### 8.2 Expanded reasons

If the status is `failed` or `deferred`, the expanded reason should translate internal failure posture into calm operator language.

It should prefer:

- why this item is in the current state
- whether waiting or retry is the expected next move

It should avoid:

- stack traces
- raw provider errors unless no calmer summary exists

## 9. Data Contract Direction

This phase should stay bounded by extending existing bundle payloads rather than inventing a separate enrichment-detail API.

The existing `/api/bundles` payload can grow with quiet-detail fields such as:

- `enrichment_summary`
- `enrichment_primary_domain_suggestion`
- `enrichment_related_domains_suggestion`
- `enrichment_topic_tags`
- `enrichment_entity_hints`
- `enrichment_status_reason`

The exact naming can follow the current service-layer style, but the principle should be:

`One bundle payload should provide both the collapsed preview and the expanded detail.`

## 10. UI Placement

### 10.1 `摘要`

`摘要` stays unchanged in this phase.

It may continue to show only:

- status
- last updated time

It should not gain:

- preview sentences
- inline detail expansion
- enrichment operator controls

### 10.2 `收件匣`

`收件匣` is the only Workbench surface that gains quiet per-bundle enrichment detail in this phase.

The detail should appear inline inside the existing bundle row presentation.

This should feel like:

- a little more understanding
- not a second control panel

## 11. Interaction Model

### 11.1 Toggle behavior

The user can expand and collapse detail per bundle row through:

- `查看詳情`
- `收起詳情`

The default state is collapsed.

### 11.2 Recovery controls relationship

If a bundle currently shows `重試` / `清除`, the quiet detail should coexist with those controls without crowding the row.

The intended precedence is:

- row remains readable first
- actions remain visible when meaningful
- detail remains optional

## 12. Copy And Tone

This phase should use concise Traditional Chinese copy.

Recommended labels:

- `查看詳情`
- `收起詳情`
- `整理摘要`
- `建議領域`
- `主題與實體`
- `目前狀態說明`
- `最後更新`

The tone should feel:

- calm
- operational
- not overly technical

## 13. Verification Standard

This phase is only acceptable if it is verified in three layers:

1. service / API tests for new quiet-detail fields
2. front-end tests or targeted script verification for preview and expand/collapse behavior
3. live browser verification in `收件匣`

Live verification should confirm:

- `摘要` remains unchanged
- `收件匣` shows one-line quiet previews without overwhelming the list
- expanded rows show interpretation-focused detail
- technical routing fields remain hidden from the default view
- retry / dismiss controls still remain usable when present

## 14. Definition Of Done

This phase is done when:

- `收件匣` shows a quiet per-bundle enrichment preview
- preview content stays compact and non-disruptive
- users can expand inline detail per bundle row
- expanded detail explains results and reasons, not backend internals
- `摘要` remains overview-first and unchanged
- existing retry / dismiss controls continue to work without visual clutter
- docs and implementation stay aligned

## 15. Next Step After This Spec

Once this spec is approved, the next step should be:

- write a small implementation plan for:
  1. bundle payload extension tests
  2. quiet-detail field wiring from enrichment sidecar data
  3. `收件匣` preview + expand/collapse UI
  4. live browser verification and docs sync
