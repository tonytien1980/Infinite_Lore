# macOS App Shell Polish Specification

**Status:** Approved for implementation
**Date:** 2026-04-11
**Project:** Infinite Lore

## 1. Purpose

This specification defines the next polish phase after the first delivered `macOS App Shell`.

The packaged shell now works locally, but it is still closer to:

- a successful engineering packaging pass

than to:

- a stable desktop product surface ready for wider everyday use

So this phase is not about adding more product features.

It is about making the desktop shell:

- less dependent on the current development layout
- more stable during launch and failure paths
- more coherent as a real macOS application

## 2. Why This Phase Comes Next

The first desktop shell already proves these things:

- the Workbench can be wrapped into a single macOS app window
- the app can manage the embedded local server
- the app can launch from source
- the packaged `.app` can be built and opened locally

That means the next highest-value work is not notarization yet.

The next highest-value work is to reduce the gap between:

- `it works on this machine in the local repo`

and

- `this behaves like a dependable app`

## 3. Scope Order

This polish phase should proceed in this order:

1. app independence from the current `<vault>/dist/Infinite Lore.app` assumption
2. startup and error experience
3. window polish and desktop product feel

This order is intentional.

If the app still depends too much on the local build layout, visual polish is secondary.

If launch and failure behavior are still rough, distribution hardening is premature.

## 4. Problem 1: App Independence

### 4.1 Current limitation

The delivered local build currently works best when the app stays in the repo build layout:

- `<vault>/dist/Infinite Lore.app`

That is good enough for proving the shell works, but it is not yet the right long-term product posture.

### 4.2 What needs to improve

The app should become less dependent on the build folder structure.

The user should not have to think:

- “I must keep the app inside this repo path or it breaks.”

### 4.3 Polish goal

This phase should introduce a better vault-resolution strategy for the desktop shell.

The user experience goal is:

- app can still auto-find the current working vault in the common local case
- if it cannot, the failure is explicit and recoverable
- the app should move closer to a product that can live outside the repo tree

The recommended fallback is:

- show a simple `選擇知識庫資料夾` picker
- let the user choose the vault root once
- remember that choice for future launches

### 4.4 What this phase should not do

This phase should not create a giant new setup wizard or account system.

It should remain local and lightweight.

## 5. Problem 2: Startup And Error Experience

### 5.1 Current limitation

The current shell is technically functional, but startup behavior is still engineering-flavored.

For example:

- startup work happens mostly invisibly
- failure messaging is still too raw
- there is not yet a polished desktop feeling around waiting, retry, or failure

### 5.2 Polish goal

The desktop shell should communicate its state clearly during:

- launching
- waiting for embedded server readiness
- vault discovery failure
- server boot failure
- webview boot failure

### 5.3 Desired user experience

The app should feel like:

- “I know what it is doing”
- “If something is wrong, it tells me clearly”

Not:

- “It flashed, stalled, or disappeared and I do not know why”

### 5.4 Output posture

Error handling should become:

- concise
- readable
- Traditional Chinese first
- product-facing, not traceback-facing

## 6. Problem 3: Window And Product Feel

### 6.1 Current limitation

The current desktop shell uses the Workbench UI as-is inside a macOS window.

That is good enough for a first delivered shell, but there are still likely polish gaps in:

- initial window sizing
- minimum size behavior
- title behavior
- app icon consistency
- loading state feel
- the overall sense that this is a real macOS tool rather than a hidden browser container

### 6.2 Polish goal

The window layer should feel:

- calmer
- more intentional
- more productized

### 6.3 Boundaries

This phase is still not about adding many native app features.

It is about improving the first windowed product feel of the current shell.

## 7. Recommended Product Direction

The recommended `app shell polish` direction is:

- keep the architecture simple
- improve local robustness first
- add only the native shell details that clearly improve trust and usability

This phase should avoid:

- large native rearchitecture
- menu-bar complexity
- multiple windows
- updater work
- notarization work

Those can come after the shell feels stable and product-like.

## 8. Proposed Phase Breakdown

### 8.1 Phase A: vault independence hardening

Focus on:

- stronger vault discovery rules
- clearer fallback path when the vault cannot be resolved
- reducing reliance on the build folder location

### 8.2 Phase B: startup and failure UX

Focus on:

- launch splash or loading state
- readable startup status
- user-facing error window or error view
- clearer recovery actions

### 8.3 Phase C: window polish

Focus on:

- title and icon consistency
- window size and minimum size tuning
- initial positioning and presentation
- small shell-level trust signals

## 9. UX Principles

The polished shell should feel:

- trustworthy
- calm
- local-first
- macOS-native enough without becoming over-engineered

The shell should not feel:

- fragile
- temporary
- developer-only
- visually noisy

## 10. Explicitly In Scope

This polish phase may include:

- better vault discovery strategy
- better launch-state messaging
- better startup error handling
- better window defaults
- better app icon or shell-level assets
- shell-level Traditional Chinese polish

## 11. Explicitly Out Of Scope

This phase does **not** include:

- codesign
- notarization
- auto update
- startup-at-login
- native notifications
- drag-and-drop file open
- menu-bar app mode
- multi-window workspace support
- backend feature expansion unrelated to the shell

## 12. Definition Of Done

This polish phase is done when:

- the desktop shell no longer feels tied to one fragile local launch layout
- startup and failure states are product-readable
- the app window feels materially more like a finished macOS tool
- the shell remains compatible with the current Workbench and vault behavior

## 13. Next Step After This Phase

Once this polish phase is complete, the likely next step becomes:

- notarization / distribution hardening

At that point, desktop packaging quality is strong enough that release-hardening work becomes worth doing.
