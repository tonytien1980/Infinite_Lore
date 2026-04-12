# Quiet Enrichment Detail Polish

**Status:** Draft for review
**Date:** 2026-04-12  
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next micro-phase after the delivered quiet enrichment detail Inbox baseline.

Its purpose is not to expand enrichment capability.

Its purpose is to make the existing quiet-detail interaction feel steadier and less distracting in daily use.

The target is:

- preserve focus when the user toggles detail
- reduce visible flicker from full-list rerenders
- keep the visual language calm and consultant-like

## 2. Why This Comes Next

The current delivered baseline already provides:

- quiet preview only when meaningful detail exists
- inbox-only `查看詳情` / `收起詳情`
- interpretation-focused inline detail
- separation between quiet `status_reason` and raw failure text

The remaining issues are smaller, but they affect feel:

- expanding or collapsing detail currently redraws the whole list
- that can reset focus and create light flicker on longer lists
- detail chips are usable now, but still a little louder than the rest of the Workbench

This means the next best step is not more enrichment information.

It is polish that protects the low-noise posture we just established.

## 3. Recommended Approach

Approved approach:

`interaction polish without expanding product surface`

This means:

- keep the same Inbox-only quiet-detail feature set
- keep the same payload contract
- improve interaction behavior and visual restraint inside the existing row

Why this is preferred:

- it improves daily use without reopening architecture
- it avoids inventing a new management surface
- it protects the current calm reading rhythm instead of adding more UI

## 4. Core Principle

This phase should follow one rule:

`Make the existing interaction steadier, not bigger.`

Applied concretely:

1. toggling detail should not feel like the whole page moved
2. keyboard and pointer users should keep their place
3. visual changes should reduce emphasis, not add novelty

## 5. Scope

This phase includes:

### 5.1 Focus retention

After `查看詳情` / `收起詳情`:

- focus should remain on the same toggle control
- keyboard users should not lose their place in the list

### 5.2 Reduced rerender pressure

The implementation should avoid unnecessary whole-list redraw behavior when a single bundle row is toggled.

The desired outcome is:

- less visible flicker
- less layout churn
- steadier perceived interaction

### 5.3 Visual restraint pass

The current quiet-detail visual layer should be tuned further toward:

- lower contrast
- less pill-like emphasis
- better alignment with the rest of the Workbench shell

## 6. Explicit Non-Goals

This phase does **not** include:

- new enrichment data fields
- new detail sections
- new bundle actions
- a dedicated detail page
- bulk expand / collapse
- animation-heavy transitions
- changing the summary page

## 7. UX Targets

### 7.1 Toggle behavior

The toggle should feel:

- immediate
- stable
- local to the row being changed

It should not feel like:

- the whole Inbox refreshed
- the user lost their cursor or scroll intent

### 7.2 Row readability

Collapsed rows should remain easy to scan:

- title
- primary domain
- bundle path / review / status
- optional quiet preview
- optional action cluster

Expanded rows should still feel subordinate to the row header, not like a second screen.

### 7.3 Visual tone

The detail area should continue to feel:

- professional
- restrained
- informational

It should move slightly away from:

- bright accent chips
- attention-grabbing contrast
- decorative emphasis

## 8. Verification Standard

This phase is only acceptable if it is verified in three layers:

1. front-end contract coverage for focus-stable behavior or equivalent guardrails
2. script / syntax verification
3. live browser verification in `收件匣`

Live verification should confirm:

- toggling detail keeps the user anchored on the same row
- interaction no longer feels like a whole-list refresh
- quiet-detail visuals remain readable but more restrained than before

## 9. Definition Of Done

This phase is done when:

- Inbox detail toggle keeps focus reliably enough for keyboard use
- visible flicker from toggle interaction is reduced
- detail visuals are calmer than the current shipped baseline
- no new product surface is introduced
- docs and implementation stay aligned

## 10. Next Step After This Spec

Once this spec is approved, the next step should be:

- write a very small implementation plan for:
  1. focus / rerender contract tests
  2. local row-toggle implementation adjustment
  3. visual restraint CSS pass
  4. live verification and docs sync
