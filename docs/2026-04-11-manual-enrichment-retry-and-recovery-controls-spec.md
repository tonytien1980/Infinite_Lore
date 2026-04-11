# Manual Enrichment Retry And Recovery Controls

**Status:** Delivered and verified locally
**Date:** 2026-04-11  
**Project:** Infinite Lore

**Delivery note:** The delivered version is intentionally bounded:

- single-bundle inline controls only
- `摘要` remains read-only
- `收件匣` provides `重試` / `清除` for active `failed` / `deferred` queue entries
- `清除` removes only the active queue entry and keeps the raw bundle plus `enrichment.json` sidecar intact
- action visibility follows true active queue state, so historical failed / deferred sidecars can remain visible without still showing controls

## 1. Purpose

This specification defines the next phase after the delivered background raw enrichment lane.

Its purpose is to turn enrichment from:

- visible
- and automatically processed

into something the user can also recover manually when it gets stuck in:

- `failed`
- `deferred`

This phase is about restoring operator control, not adding more model orchestration.

## 2. Why This Comes Next

The current product already provides:

- automatic queueing of new raw bundles
- a bounded server-owned background enrichment worker
- honest enrichment states:
  - `pending`
  - `completed`
  - `failed`
  - `deferred`
- status visibility in:
  - `摘要`
  - `收件匣`

What is still missing is the user’s ability to act on those states.

Right now the product can tell the user:

- this bundle failed
- this bundle was deferred

but it cannot yet let the user do the two most natural next actions:

- retry after fixing settings or a transient problem
- dismiss or recover a stuck queue entry when it should no longer stay active

That makes the next most valuable step operational, not architectural.

## 3. Recommended Approach

Approved approach:

`inline single-bundle controls inside existing Workbench surfaces`

This means:

- keep `摘要` read-only and compact
- add actionable controls in `收件匣`
- scope controls to one bundle at a time

Why this is preferred:

- it fits the current Workbench posture
- it avoids a dedicated queue-management page
- it keeps user attention on the same raw bundle list they already use
- it solves the highest-value operator gap with the least surface area

## 4. Core Principle

This phase should preserve the current honesty rules:

1. retry must not fake success
2. dismiss must not delete the raw bundle
3. queue state changes must stay explicit and recoverable
4. status text and action affordances must match the true queue state

The operating rule is:

`Visible state should always have an operator action when action makes sense.`

## 5. Scope

This phase includes:

### 5.1 Retry control

For `failed` and `deferred` bundle entries:

- the user can requeue that bundle manually
- the bundle returns to `pending`
- the background worker can pick it up again on the next cycle

### 5.2 Dismiss / recovery control

For `failed` and `deferred` bundle entries:

- the user can remove the active queue entry without deleting the raw bundle
- the sidecar remains as history
- the queue stops treating that bundle as active work

This is the bounded recovery action for entries that should no longer keep occupying queue state.

### 5.3 UI status + controls

This phase should add action controls only where they are most useful:

- `收件匣` bundle list

`摘要` should remain status-focused rather than becoming an operations console.

## 6. Explicit Non-Goals

This phase does **not** include:

- bulk retry
- bulk dismiss
- a new enrichment-management page
- retry scheduling policies
- pause / resume queue controls
- provider selection controls at action time
- editing the enrichment sidecar by hand
- deletion of raw bundles through enrichment controls

## 7. Bundle Action Model

### 7.1 Retry

Retry should:

- require a concrete `bundle_path`
- rebuild the active queue entry for that bundle
- reset bundle status back to `pending`
- clear transient failure messaging in the active queue entry

Retry should be allowed for:

- `failed`
- `deferred`

Retry should not appear for:

- `pending`
- `completed`

### 7.2 Dismiss

Dismiss should:

- require a concrete `bundle_path`
- remove the active queue entry for that bundle
- leave the raw bundle intact
- leave the sidecar as historical trace

Dismiss is a queue recovery action, not a knowledge deletion action.

## 8. Queue Semantics

The queue state file should continue to be the operational source of truth for active work.

After this phase:

- retry adds or refreshes an active `pending` entry
- dismiss removes the active entry
- completed items are still removed by the worker
- failed / deferred items remain operator-visible until retried or dismissed
- historical failed / deferred sidecars can remain visible after dismiss, but they are no longer actionable once the active queue entry is gone

## 9. API Surface

This phase should add small action endpoints rather than a large enrichment API.

Recommended endpoints:

- `POST /api/enrichment/retry`
- `POST /api/enrichment/dismiss`

Each should accept:

- `bundle_path`

### 9.1 Retry response

Should return enough information for UI refresh:

- `bundle_path`
- `enrichment_status`
- `enrichment_updated_at`

### 9.2 Dismiss response

Should return enough information for UI refresh:

- `bundle_path`
- `dismissed: true`

## 10. Service-Layer Behavior

The backend action helpers should be narrow and explicit.

Recommended behavior:

- resolve bundle path relative to vault root
- reject paths outside the vault
- operate only on raw bundle directories
- update queue state atomically
- avoid mutating unrelated queue entries

## 11. UI Placement

### 11.1 Summary page

`摘要` should remain read-only.

It may show:

- status
- last updated time

But not action buttons.

### 11.2 Inbox bundle list

`收件匣` should render action buttons only when meaningful:

- `重試` for `failed` / `deferred`
- `清除` for `failed` / `deferred`

In the delivered implementation, these controls are additionally gated by active queue state:

- if a bundle still has an active failed / deferred queue entry, show the controls
- if the bundle only has historical failed / deferred sidecar state after dismiss, keep the status visible but hide the controls

These should appear inline with the existing bundle row rather than as a separate detail drawer in this phase.

## 12. Copy And UX Tone

Controls should use direct Traditional Chinese labels:

- `重試`
- `清除`

Status feedback should stay brief and operational:

- `已重新排入背景處理`
- `已從待處理佇列清除`

Do not over-explain scheduler internals in the interface.

## 13. Error Handling

Retry should fail clearly when:

- `bundle_path` does not exist
- `bundle_path` is outside the vault
- target is not a bundle directory

Dismiss should fail clearly when:

- `bundle_path` is invalid
- there is no matching active queue entry

The UI should surface these as honest action failures, not silently refresh.

## 14. Verification Standard

This phase is only acceptable if it is verified in three layers:

1. queue action unit tests
2. API tests for retry and dismiss
3. live browser verification in `收件匣`

Delivered local verification included:

- queue helper tests in `tests.test_raw_enrichment`
- retry / dismiss API tests in `tests.test_workbench_api`
- local-only live browser verification on an isolated temp vault with a local temp Workbench server and temp Playwright runner that confirmed:
  - `摘要` stays read-only
  - `收件匣` shows inline controls only for active failed / deferred entries
  - `重試` returns a bundle to visible `pending`
  - `清除` removes the active queue entry without deleting the bundle
- this verification did not include production deployment checks or live OpenAI enrichment execution

## 15. Definition Of Done

This phase is done when:

- failed and deferred raw enrichment entries can be retried manually
- failed and deferred raw enrichment entries can be dismissed from active queue state
- retry returns the bundle to `pending`
- dismiss removes the active queue entry without deleting the raw bundle
- `收件匣` shows inline controls only when meaningful
- `摘要` remains status-only
- docs and implementation stay aligned

## 16. Next Step After This Spec

Once this spec is approved, the next step should be:

- write a small implementation plan for:
  1. queue action tests
  2. retry / dismiss API helpers
  3. Workbench inbox action wiring
  4. live verification and docs sync
