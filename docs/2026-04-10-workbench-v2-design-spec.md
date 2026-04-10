# Workbench V2 Design Specification

**Status:** Approved for implementation
**Date:** 2026-04-10
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next design phase for `Infinite Lore Workbench`.

The goal is not to add another backend lane first.

The goal is to redesign the product surface so the system already built underneath can become:

- better looking
- easier to use
- more coherent as a product
- easier to later package into a real macOS desktop application shell

This is a product-design reset, not a backend expansion.

## 2. Why Workbench V2 Is The Right Next Move

The current system already has:

- raw import
- compile
- grounded Ask / Query
- reflection / correction
- source scanning
- relation-aware retrieval
- multimodal intake
- image OCR

The biggest remaining gap is no longer core capability.

The biggest gap is product experience.

The current Workbench is usable, but it still feels closer to:

- a local operational tool
- a localhost utility surface

than to:

- a polished knowledge workbench the user would genuinely want to open every day

So the next highest-value move is to redesign the Workbench around the real working flow.

## 3. Approved Product Direction

The approved direction for Workbench V2 is:

`Ask-first, desktop-first, Traditional Chinese-first knowledge workbench`

This means:

- the main working surface becomes the true homepage
- the product is designed with a later macOS application shell in mind
- the entire main interface should default to Traditional Chinese
- reading quality matters as much as functional power

Workbench V2 should not feel like:

- a generic admin dashboard
- a raw browser app with too many equal-weight pages
- a crowded graph console

## 4. Design Principles

Workbench V2 should feel like:

- professional consultant software
- a research-oriented reading desk
- a trustworthy local knowledge tool

The design should emphasize:

- calm structure
- readable answer surfaces
- clear evidence visibility
- low-friction follow-up work

The design should avoid:

- clutter-first dashboards
- over-dense control panels
- visually loud “AI tool” patterns
- mixed-language UI on primary controls

## 5. Language Rule

Workbench V2 should default to Traditional Chinese across the main interface.

This applies to:

- navigation labels
- page titles
- buttons
- empty states
- status messages
- form labels

English may remain only where it is truly necessary in secondary technical contexts, but it should not dominate primary navigation or core action labels.

## 6. Desktop-First Rule

Workbench V2 should be designed as a `macOS desktop-first` product surface even before the desktop shell is packaged.

This means:

- the visual composition should assume an application window, not a generic browser page
- sidebar and top chrome should feel like a workstation shell
- page widths, panel spacing, and working rhythms should favor sustained desktop use

This phase does not yet require packaging the application shell.

But the design must be compatible with that later shell from the start.

## 7. New Information Architecture

The approved navigation model is:

1. `首頁`
2. `摘要`
3. `收件匣`
4. `知識庫`
5. `系統`
6. `設定`

This replaces the old mental model where:

- `Home`
- `Ask`

acted like two competing primary pages.

### 7.1 `首頁`

`首頁` becomes the true primary work surface.

This page is no longer a shallow dashboard.

It is the main Ask workspace.

### 7.2 `摘要`

The previous `Home` dashboard-like content moves into `摘要`.

Its purpose is:

- recent activity
- system summary
- operational snapshot
- quick orientation

It is useful, but no longer the product’s main destination.

### 7.3 `收件匣`

`收件匣` remains the raw intake and source-management surface.

Its role is:

- import
- source configuration
- `Scan now`
- retry and queue monitoring

### 7.4 `知識庫`

`知識庫` remains the compile-output view.

Its role is:

- recent synthesis notes
- recent small-note updates
- lineage visibility

### 7.5 `系統`

`系統` remains the operational and health page.

### 7.6 `設定`

`設定` remains the local configuration and model-routing page.

## 8. Homepage Role Reset

The biggest Workbench V2 change is:

`首頁 = Ask Workspace`

This is the most important IA decision in the redesign.

Why:

- it matches the real user workflow
- it avoids having two pseudo-homepages
- it makes the product feel intentional instead of fragmented

## 9. Homepage Layout Direction

The approved homepage direction is:

`Top / Middle / Bottom working layout`

Not:

- three narrow parallel columns
- dashboard cards first
- giant always-open prompt box

### 9.1 Top region

The top region should contain a compact prompt bar.

This region should include:

- question input
- answer mode
- follow-up entry
- recent question access

After an answer is returned, this prompt area should remain visible but compact.

It should not dominate the screen.

### 9.2 Middle region

The middle region should be the main answer surface.

This should be the visual center of the page.

It should be:

- wide
- readable
- document-like
- suitable for sustained reading

This region should contain:

- the answer itself
- answer-level limits and uncertainty
- follow-up actions related to the answer

### 9.3 Lower evidence region

Below the answer, the next region should hold evidence and traceability.

This region should combine:

- grounding
- source trace
- relation trace

into a coherent evidence section rather than multiple tiny side boxes.

The design goal is:

- show why the answer is trustworthy
- keep evidence visible without visually crushing the answer

### 9.4 Lower work region

Below the evidence region, the next region should hold the user’s action area.

This region should contain:

- recent reflections
- correction drafting
- reflection drafting
- draft review
- confirm / discard actions

The design goal is:

- let the user continue working after reading
- keep the “my interpretation / my correction” layer visibly separate from the library answer

## 10. Why The Layout Is Vertical

The user explicitly rejected a three-column parallel layout because it makes every area too narrow and hurts readability.

That judgment is correct for this product.

Workbench V2 should prioritize:

- reading quality
- cognitive flow
- vertical work rhythm

over:

- maximum simultaneous visibility of every panel

The working order should feel natural:

`ask -> read -> inspect evidence -> respond`

That sequence is inherently top-to-bottom.

## 11. Visual Direction

The approved visual direction is a hybrid of:

- professional consultant software
- research reading desk

Meaning:

- bright and restrained base
- strong typography hierarchy
- generous whitespace
- crisp layout structure
- low visual noise

The surface should not look like:

- a dark hacker console
- a crowded BI dashboard
- a playful consumer AI product

## 12. Reference Products To Borrow From

Workbench V2 should borrow selectively from several products.

### 12.1 NotebookLM

Borrow:

- source-grounded answering posture
- evidence-first trust model
- question flow tied closely to a corpus

Do not borrow:

- educational-tool tone
- notebook metaphor as the whole product identity

### 12.2 Readwise Reader

Borrow:

- reading quality
- intake-to-reading continuity
- annotation-friendly posture

Do not borrow:

- a pure reading-app identity

### 12.3 Heptabase

Borrow:

- research workbench feeling
- deliberate thought-supporting layout

Do not borrow:

- whiteboard-first navigation

### 12.4 Reflect

Borrow:

- low-friction interaction
- clean surface
- reduced interface anxiety

Do not borrow:

- an overly minimal product that hides evidence-heavy power too much

## 13. Interaction Principles

### 13.1 Answer-first after submission

Once a question is submitted, the interface should visually shift attention to the answer, not stay dominated by the input box.

### 13.2 Evidence is visible, not buried

Trust depends on visible grounding.

The evidence region should be easy to inspect without opening separate pages or drawers for normal use.

### 13.3 Personal work stays separate from source-grounded answer

Reflections and corrections should remain visually distinct from the answer itself.

### 13.4 Fewer competing primaries

The page should not present too many equal-weight calls to action at once.

### 13.5 Desktop calm first, mobile fold second

The desktop layout should be optimized first.

Mobile can stack the same regions vertically in the same logical order:

- prompt
- answer
- evidence
- my work

## 14. Page Role Summary

### `首頁`

Main daily workbench.

### `摘要`

Recent activity, quick orientation, and system snapshot.

### `收件匣`

Import, sources, queue, retry, `Scan now`.

### `知識庫`

Compiled notes and lineage review.

### `系統`

Health, runtime, warnings.

### `設定`

Provider, model routing, local app behavior.

## 15. Out Of Scope For This Design Phase

This design phase should not yet decide:

- exact Electron / Tauri / shell packaging choice
- final macOS chrome implementation
- deeper connector platform build-out
- graph UI
- additional multimodal lanes

Those are adjacent but separate decisions.

## 16. Definition Of A Successful V2 Direction

Workbench V2 design is successful if:

- the homepage clearly becomes the main work surface
- the product feels less like a localhost utility and more like a real application
- answer reading quality improves materially
- evidence remains visible and trustworthy
- reflection and correction remain easy to use without polluting the answer
- the UI is predominantly Traditional Chinese
- the visual structure is compatible with later macOS app-shell packaging
