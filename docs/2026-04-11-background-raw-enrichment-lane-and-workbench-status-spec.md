# Background Raw Enrichment Lane And Workbench Status Visibility

**Status:** Delivered and verified locally
**Date:** 2026-04-11  
**Project:** Infinite Lore

**Delivery note:** The delivered version is intentionally bounded:

- one server-owned background worker
- poll interval `15` seconds
- batch size `1`
- enrichment status visible in existing `摘要` and `收件匣` surfaces
- no daemon, launchd job, retry UI, or multi-worker scheduler in this phase

## 1. Purpose

This specification defines the next phase after the locally delivered `raw enrichment + multi-provider routing` baseline.

Its purpose is to close the remaining gap between:

- a bounded manual enrichment runner
- and a product-feeling background enrichment lane

without overbuilding a scheduler platform.

This phase should make raw enrichment feel like part of the normal Workbench lifecycle instead of a separate manual maintenance command.

## 2. Why This Comes Next

The current delivered baseline already provides:

- automatic queueing of new raw bundles
- bundle-local `enrichment.json`
- `00_System/raw-enrichment-state.json`
- honest `pending / completed / failed / deferred` states
- OpenAI shared-first enrichment execution through `tools/raw_enrichment.py`
- multi-provider settings and route structure

But the current posture is still limited:

- enrichment execution is manual
- Workbench does not yet clearly surface enrichment state in the normal UI
- there is no server-owned background lane that quietly drains the queue while the product is open

That means the next highest-value improvement is not more provider breadth first.

It is to turn the existing truthful queue and runner into a lightweight background lane and expose enrichment state where the user already works.

## 3. Recommended Approach

Approved approach:

`server-owned lightweight background worker`

This means:

- the Workbench server owns a small background poller
- the poller periodically checks `raw-enrichment-state.json`
- each cycle processes only a very small number of pending bundles
- import and scan continue to queue work only
- the UI reads the current enrichment state through existing bundle/dashboard APIs

Why this approach is preferred:

- it feels like a real product improvement instead of a maintenance script
- it reuses the queue and runner already delivered
- it keeps the architecture honest and small
- it avoids turning `Scan now` into a hidden long-running synchronous job

## 4. Core Principle

The phase should preserve these rules:

1. `raw preservation` still happens before any model execution
2. `import` and `scan` still succeed even if enrichment is unavailable
3. background enrichment must stay bounded and polite
4. enrichment state shown in the UI must reflect the real queue state honestly

The product rule stays:

`Preserve first. Queue second. Enrich in the background.`

## 5. Scope

This phase includes two connected changes:

### 5.1 Background enrichment lane

- a lightweight server-owned poller
- periodic draining of pending enrichment work
- bounded execution per cycle

### 5.2 Workbench status visibility

- expose enrichment status through existing API payloads
- show enrichment state in the existing Workbench surfaces where raw bundles already appear

## 6. Explicit Non-Goals

This phase does **not** include:

- launchd jobs
- a separate daemon process
- distributed queue infrastructure
- full retry scheduling policy redesign
- manual retry UI
- provider-specific execution for every model backend
- homepage model controls
- real-time progress bars

This is a product lane, not a job orchestration platform.

## 7. Background Worker Shape

The first background lane should be intentionally small.

### 7.1 Ownership

The worker should be owned by the local Workbench server lifecycle.

It should:

- start when the local Workbench server starts
- stop when the local Workbench server stops
- do nothing when the server is not running

### 7.2 Poll behavior

Recommended defaults:

- poll interval: `15` seconds
- batch size per cycle: `1` bundle

Reason:

- simple enough to reason about
- low risk for duplicate work
- sufficient for a single-user desktop-local product

### 7.3 Concurrency posture

The first version should be single-worker only.

There should be no attempt to process multiple bundles in parallel.

## 8. State Model

This phase should keep the current bounded status vocabulary:

- `pending`
- `completed`
- `failed`
- `deferred`

This phase should **not** introduce a richer live scheduler contract such as:

- `running`
- `retry_scheduled`
- `cancelled`

Those are future concerns unless they become necessary.

## 9. Processing Rules

### 9.1 When to process

The worker should only process entries already present in:

- `00_System/raw-enrichment-state.json`

It should not invent new queue entries.

### 9.2 When to dequeue

Only `completed` bundles should be removed from `pending_bundles`.

`failed` and `deferred` bundles should remain visible in the queue state until a later policy decides otherwise.

### 9.3 When to skip

If `enrich_raw` resolves to:

- no runnable provider
- or a non-OpenAI provider

the worker should keep the bundle in queue as `deferred`.

This phase does not pretend those providers are executable.

## 10. API Visibility

The current APIs already expose raw bundles and dashboard summaries.

This phase should extend those payloads rather than inventing a separate enrichment page first.

### 10.1 Bundle list

`/api/bundles` entries should include:

- `enrichment_status`
- `enrichment_provider`
- `enrichment_model`
- `enrichment_failure_reason`
- `enrichment_updated_at`

### 10.2 Dashboard recent imports

Recent import summaries should include at least:

- `enrichment_status`
- `enrichment_updated_at`

This lets the user see whether newly imported material is still pending or already enriched.

## 11. UI Visibility

The first visibility slice should stay inside existing surfaces:

- `摘要`
- `收件匣`

Recommended behavior:

- recent imports show enrichment state text
- bundle list shows enrichment state text
- failed / deferred state should be visible, not hidden

This phase should not add a whole new Workbench page.

## 12. Error Handling

The background lane must remain honest:

- missing bundle paths -> `failed`
- unreadable bundle files -> `failed`
- malformed model output -> `failed`
- unsupported provider -> `deferred`
- no runnable provider -> `deferred`

The UI should reflect these states through the payload fields rather than inventing friendlier fake success.

## 13. Verification Standard

This phase is only acceptable if it is verified in three layers:

1. queue / runner unit tests
2. API visibility tests
3. live browser-level verification that status changes actually surface in the Workbench

## 14. Definition Of Done

This phase is done when:

- Workbench server automatically drains pending enrichment work in the background
- import and scan still do not block on enrichment
- completed bundles leave the queue
- failed and deferred bundles remain honestly visible
- `/api/bundles` exposes enrichment status fields
- dashboard recent imports expose enrichment status fields
- the existing Workbench UI shows those statuses without adding model clutter
- docs and implementation stay aligned

## 15. Next Step After This Spec

After this delivered phase, the next step should be one of:

- manual retry / recovery controls for failed and deferred enrichment
- richer per-bundle enrichment detail in the Workbench
- later provider-specific execution beyond the current OpenAI shared-first path
