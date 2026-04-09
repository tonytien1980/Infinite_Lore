# Automation And Watcher Layer Specification

**Status:** Draft v1 for review  
**Date:** 2026-04-09  
**Project:** Infinite Lore

## 1. Purpose

This subsystem defines the first practical automation layer for `Infinite Lore`.

Its job is to make source intake feel lighter and more continuous without turning the system into a heavy always-on crawler platform.

The first version should:

- let the user trigger one-step scanning from the Workbench
- pull from both local intake and configured web sources
- deduplicate incoming material before import
- run `import + compile` in the same top-level flow
- retry previously failed items without extra manual cleanup
- keep the workflow lightweight, observable, and optional

## 2. Product Role

This layer is:

- a practical automation helper
- an intake accelerator
- a lightweight connector runner
- a bridge between source discovery and the existing `raw -> wiki -> ask` pipeline

This layer is not:

- a mandatory background daemon
- a full crawler platform
- a deep web scraping system
- a graph-first engine
- a replacement for the current manual import path

## 3. Core Principle

Automation should reduce friction, not create a new control burden.

Three hard rules:

1. The primary user action is still simple: press `Scan now`.
2. Scan runs should be lightweight and observable.
3. Expensive or ambiguous source work should be deferred rather than hidden behind heavy loops.

## 4. Approved Scope

The first implementation is the `Practical Automation Layer`.

It includes:

- manual `Scan now`
- optional lightweight scheduled scans later
- source connectors for:
  - local intake folder
  - RSS / feed sources
  - article list pages / blog archive pages
- deduplication
- import + compile in one flow
- retry of failed items
- lightweight cache and incremental behavior
- visible scan results in the existing Workbench `Inbox`

It does not include:

- unrestricted deep crawling
- full connector orchestration
- source analytics dashboards
- complex scheduling control
- graph UI

## 5. Primary Operating Model

The approved first-version operating model is:

`manual scan first`

Meaning:

- the user thinks of new material
- the user presses `Scan now`
- the system scans configured intake sources
- the system deduplicates findings
- the system performs `import + compile`
- the Inbox reflects what happened

The system may later add light scheduled scans, but the first design center is the manual scan flow.

## 6. Source Scope

The scan layer must combine two intake families.

### 6.1 Local intake

Local intake means:

- existing local files placed in `20_Raw/inbox/`
- files added through the current Workbench upload flow

### 6.2 Configured source connectors

The first connector family includes:

- `RSS / feed sources`
- `article list pages / blog archive pages`

Only explicitly configured sources are scanned.

The system must not behave like an unrestricted crawler.

## 7. Connector Boundary Rules

### 7.1 RSS / feed sources

These are first-class sources in Phase 7.

They should be treated as the most mature first-version connector type because:

- they are structured
- they support incremental polling cleanly
- they make deduplication easier

### 7.2 Article list pages / blog archive pages

These are supported in the same phase, but with tighter boundaries.

First-version rule:

- the user provides one list page URL
- the system extracts recognizable article links from that page
- the system does not automatically deep-crawl beyond that page

This keeps the connector practical without turning Phase 7 into a crawler platform.

## 8. Scan Behavior

When the user presses `Scan now`, the system should:

1. inspect local intake and configured connectors
2. identify candidate new items
3. deduplicate them
4. run `import + compile` for accepted items
5. retry previously failed items
6. present a compact result summary in the Inbox

The scan should not stop at raw capture only.

The approved behavior is:

`scan -> deduplicate -> import -> compile`

## 9. Retry Behavior

The first version should automatically include failed items in scan retries.

Reason:

- the user should not have to remember separate cleanup steps
- retry belongs to the same practical flow as new intake

However:

- retry should remain bounded
- the system should surface repeated failures clearly instead of retrying forever without visibility

## 10. Deduplication Rules

The first-version deduplication rule is:

`canonical URL first, content hash second`

This is needed because the same article may appear through:

- RSS
- a list page
- a manually supplied URL

Deduplication should therefore check:

1. canonical article URL when available
2. normalized source URL fallback
3. content hash after retrieval

The goal is not perfect deduplication in all cases.

The goal is to stop the obvious duplicate paths from polluting the library.

## 11. Cache And Incremental Behavior

The Phase 7 design should adopt Graphify-inspired cache behavior selectively.

The required principles are:

- unchanged items should not be reprocessed unnecessarily
- cheap checks should happen before expensive work
- cache should support both local and connector-based intake

The first cache layers should include:

- scan discovery cache
- canonical URL seen-state
- content hash seen-state
- failed-item retry state

The system should not require a graph engine to gain these benefits.

## 12. Split-By-Cost Processing

The automation layer should classify work by cost.

### 12.1 Cheap work

- source discovery
- local file detection
- feed polling
- list-page link extraction
- dedup checks
- state transitions

### 12.2 More expensive work

- article fetch and normalization
- downstream import conversion
- compile
- later multimodal extraction

The system should always prefer:

`cheap detection first, expensive processing only when needed`

This is the main reason the automation layer stays practical rather than heavy.

## 13. State Model

Each candidate item discovered by automation should have a visible state.

The first version should support at least:

- `discovered`
- `deduplicated`
- `imported`
- `compiled`
- `failed`
- `skipped`

These states do not replace bundle metadata.

They sit above bundle metadata and describe the automation run outcome.

## 14. Workbench Integration

The first version should not add a new top-level page.

Source management and scan control should live inside the existing `Inbox`.

This keeps the workbench simple and matches the user's preference for low UI complexity.

The Inbox should gain:

- configured source list
- `Scan now`
- last scan result summary
- failed item count
- retry visibility
- source-level enable / disable controls

## 15. Source Management UX

The first version should support source management directly inside `Inbox`.

Each configured source should store:

- source name
- source type
- source URL
- enabled / disabled
- last checked time
- last result summary

The source types for this version are:

- `rss-feed`
- `article-list-page`

## 16. Scan Result UX

After a scan completes, the user should be able to understand quickly:

- how many new items were found
- how many were deduplicated away
- how many imported successfully
- how many compiled successfully
- how many failed

The UI should feel like:

- a calm operational summary
- not a noisy job log

Detailed logs can exist later, but the first version should optimize for clarity.

## 17. Scheduled Automation Boundary

Scheduled scans may exist in the future, but they are not the center of Phase 7.

If any scheduled behavior is added in the first implementation, it should be:

- lightweight
- optional
- understandable from the Inbox

The system should not require background automation in order to function well.

## 18. Relationship To Full Connector Platform

The `Full Connector Platform` is intentionally postponed.

That later phase may include:

- richer connector types
- deeper crawl jobs
- scheduling controls
- source analytics
- job histories
- connector-specific tuning

This later phase is a post-launch expansion target, not part of the current implementation scope.

## 19. Relationship To Graphify-Inspired Adoption

Phase 7 should absorb only the Graphify ideas that directly help practical automation:

- cache-first incremental behavior
- split-by-cost watcher logic

It should not absorb:

- graph-first UI
- export-driven workflow
- graph visualization as a primary surface

The next layer after Phase 7 should be:

- relation-aware retrieval
- confidence-labeled relations
- later multimodal expansion

## 20. Definition Of Success

Phase 7 succeeds when:

- the user can press `Scan now`
- the system scans local and configured sources together
- duplicates are filtered out reasonably
- new items run through `import + compile`
- failures are visible and retried later
- Inbox makes the result understandable without extra pages
- the system feels easier to use, not heavier
