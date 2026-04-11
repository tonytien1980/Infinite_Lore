# macOS App Shell Polish Specification

**Status:** Delivered and verified locally
**Date:** 2026-04-11
**Project:** Infinite Lore

## 1. Purpose

This specification defines the polish phase that shipped immediately after the first delivered `macOS App Shell`.

The packaged shell now works locally, but it is still closer to:

- a successful engineering packaging pass

than to:

- a stable desktop product surface ready for wider everyday use

This phase did not add new product features.

It delivered a desktop shell that is:

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

The delivered work reduced the gap between:

- `it works on this machine in the local repo`

and

- `this behaves like a dependable app`

## 3. Scope Order

This polish phase was executed in this order:

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

The app is now less dependent on the build folder structure.

The target user posture was:

- “I must keep the app inside this repo path or it breaks.”

### 4.3 Polish goal

This phase introduced a better vault-resolution strategy for the desktop shell.

The delivered user experience is:

- app can still auto-find the current working vault in the common local case
- if it cannot, the shell reuses the last confirmed vault root when available
- if automatic resolution still fails, the failure is explicit and recoverable through a picker flow
- the product can now live outside the repo tree more safely than the first shell version

The shipped fallback is:

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

The desktop shell now communicates its state clearly during:

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

Error handling is now:

- concise
- readable
- Traditional Chinese first
- product-facing, not traceback-facing

## 6. Problem 3: Window And Product Feel

### 6.1 Current limitation

The current desktop shell uses the Workbench UI as-is inside a macOS window.

That was good enough for a first delivered shell, but the polish pass closed the main gaps in:

- initial window sizing
- minimum size behavior
- title behavior
- app icon consistency
- loading state feel
- the overall sense that this is a real macOS tool rather than a hidden browser container

### 6.2 Polish goal

The delivered window layer now feels:

- calmer
- more intentional
- more productized

### 6.3 Boundaries

This phase is still not about adding many native app features.

It is about improving the first windowed product feel of the current shell.

## 7. Recommended Product Direction

The shipped `app shell polish` direction is:

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

This delivered polish phase includes:

- stronger vault discovery strategy with remembered-vault fallback
- launch-state messaging through a Traditional Chinese loading view
- startup error handling through a Traditional Chinese recovery view with retry / choose-vault / quit actions
- better window defaults for title, size, minimum size, background, and localization
- shell-level Traditional Chinese polish
- pinned shell/build dependency guidance through `packaging/macos/requirements-shell.txt`

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

`packaging/macos/requirements-shell.txt` is a verified additive shell/build baseline for the macOS packaging flow. It is not intended to replace the main project bootstrap or the broader Infinite Lore Python environment.

## 12. Definition Of Done

This polish phase is done when:

- the desktop shell no longer feels tied to one fragile local launch layout
- startup and failure states are product-readable
- the app window feels materially more like a finished macOS tool
- the shell remains compatible with the current Workbench and vault behavior
- the shell build can be re-verified with the additive pinned dependency baseline

## 13. Next Step After This Phase

Now that this polish phase is complete, the likely next step becomes:

- notarization / distribution hardening

At that point, desktop packaging quality is strong enough that release-hardening work becomes worth doing.
