# macOS App Shell Design Specification

**Status:** Delivered and verified locally
**Date:** 2026-04-11
**Project:** Infinite Lore

## 1. Purpose

This specification defines the first packaged macOS desktop shell for `Infinite Lore`.

The goal of this phase is not to redesign the product again.

The goal is to package the already-delivered `Workbench V2` into a real macOS application shell so the user can:

- double-click an app
- open directly into `首頁`
- avoid seeing a browser, localhost URL, or terminal window
- keep using the same vault and the same local workflows

This is a packaging and shell phase, not a new backend or frontend architecture phase.

## 2. Current Product Baseline

The current verified baseline already includes:

- local FastAPI Workbench runtime
- `首頁` as the main Ask workspace
- `摘要 / 收件匣 / 知識庫 / 系統 / 設定`
- grounded Ask / Query
- reflection / correction
- `Scan now`
- multimodal import
- image OCR

So the app shell should wrap the existing system rather than replace it.

This shell baseline has now been delivered and locally re-verified. The later polish pass kept this architecture intact while improving vault fallback behavior and startup/error presentation.

## 3. Approaches Considered

### 3.1 Recommended: `pywebview + FastAPI + PyInstaller onedir`

This approach keeps the current Python backend and local web UI intact.

The app shell:

- starts the local FastAPI server in-process or as a managed child runtime
- waits for the local URL to become ready
- opens a single macOS window using the system webview
- loads the local Workbench URL internally

Why this is the recommended first version:

- lowest integration risk
- smallest architecture change
- best fit for the current Python-first codebase
- fastest route from `localhost tool` to `double-clickable app`
- easiest way to preserve current behavior and current vault compatibility

### 3.2 Alternative: `Tauri + Python sidecar`

This is possible, but it adds an extra Rust/Tauri shell layer plus sidecar process management.

It is attractive later if the product needs:

- deeper native integration
- stronger updater story
- richer shell capabilities

But it is not the best first packaging move because it increases integration surface before the current product shell has even been shipped as a desktop app once.

### 3.3 Not Recommended First: `Electron + local server`

This would work, but it is heavier than needed for the current product.

The first desktop shell should reduce packaging distance, not add a large new runtime stack.

## 4. Chosen Direction

Phase 12 should use:

`pywebview + managed local FastAPI runtime + PyInstaller onedir macOS bundle`

This is explicitly a `wrap what already works` strategy.

It should not:

- reimplement the UI in native widgets
- replace FastAPI
- replace the current Workbench routing
- create a second product surface beside the browser version

## 5. Product Definition

The first macOS app shell should feel like:

- a single-purpose knowledge workbench app
- a packaged version of the delivered Workbench V2
- a local desktop tool, not a browser shortcut

The user experience should be:

1. double-click app
2. app opens a single main window
3. `首頁` loads directly
4. the current vault-backed Workbench is ready to use

The user should not need to:

- open Terminal
- manually run `python3 tools/run_workbench.py`
- copy a localhost URL into a browser

## 6. Core Requirements

### 6.1 Single main window

The first version should open one main window only.

There should be no:

- multiple document windows
- separate settings window
- tray app behavior

### 6.2 Hidden localhost

The app may still use a local HTTP server internally, but that should be implementation detail only.

The user should not see:

- `http://127.0.0.1:8765`
- a browser tab
- a terminal session

### 6.3 Existing vault compatibility

The app must keep using the same shared vault model as the current Workbench.

This means:

- same note folders
- same raw bundle flow
- same wiki compile outputs
- same Ask / reflection / correction behavior

### 6.4 Existing local config compatibility

The app should keep compatible behavior for local settings outside the vault.

It must not silently create a totally separate product identity where:

- the browser Workbench has one config
- the app shell has another unrelated config

### 6.5 Traditional Chinese first

The packaged app should continue the current rule:

- primary interface in Traditional Chinese
- no visible return to mixed-language main UI

## 7. App Lifecycle

### 7.1 Startup

When the app launches:

1. initialize app shell
2. determine the target vault and config paths
3. start the local FastAPI runtime
4. wait until the health or root page is reachable
5. open the main window

### 7.2 Runtime

During runtime:

- the server stays alive as long as the app is alive
- the webview window is the only primary surface
- the app shell should gracefully surface startup failure if the server cannot boot

### 7.3 Shutdown

When the user closes the app:

- the window closes
- the managed local runtime shuts down
- no orphan local server should remain running

## 8. Error Handling

The first app shell must handle these cases cleanly:

- server boot failure
- port already occupied
- invalid config path
- missing or unreadable vault
- webview initialization failure

The user-facing posture should be:

- clear local error messaging
- no raw crash trace as the primary surface
- no silent hang with blank white window

## 9. Scope For First Version

The first desktop shell should include:

- macOS `.app` packaging
- single main window
- managed server startup
- managed server shutdown
- direct load into current Workbench
- compatibility with the current local vault flow

## 10. Explicitly Out Of Scope

The first version does **not** include:

- auto update
- notarization / distribution-hardening as a shipped public release flow
- Dock menu customization
- native notifications
- file association handling
- drag-and-drop open-from-Finder
- menu-bar app behavior
- startup-at-login
- multi-window workspaces
- replacing browser access entirely

These can come later, but they are not required to prove the packaged shell works.

## 11. UX Principles For The App Shell

The app shell should preserve the current Workbench V2 posture:

- professional
- calm
- desktop-first
- reading-first

The shell should not add noisy chrome around the product.

The right feeling is:

- `Infinite Lore` as a real app window

Not:

- `a browser hidden inside a dev wrapper`

## 12. Data And Path Strategy

The first packaged shell should keep path behavior predictable.

Recommended direction:

- keep the same vault-root concept
- keep the same Workbench backend contract
- keep local config external to the vault, as today

The packaged app should not force a vault migration in this phase.

In the delivered local-build version, the shell now resolves the vault root automatically when the packaged app is launched from the normal build output layout:

- `<vault>/dist/Infinite Lore.app`

This keeps the first local packaged shell compatible with the current repo-backed vault without introducing a separate setup phase.

After the shipped shell-polish pass, launches outside that local build layout now fall through to:

- the last remembered valid vault root when one exists
- a `選擇知識庫資料夾` picker when automatic resolution still cannot find a valid vault

## 13. Packaging Strategy

The first packaging target should be:

- macOS only
- local user build
- `onedir` app bundle

This is preferred over a more aggressive single-file packaging posture because the goal is stability, inspectability, and low integration risk.

For local build verification, `packaging/macos/requirements-shell.txt` is the additive verified shell/build baseline for `pywebview`, `PyInstaller`, and the pinned PyObjC bridge modules used by the macOS shell. It is not a full bootstrap replacement for the wider Infinite Lore project environment.

## 14. Verification Requirements

Before this phase is considered complete, verification should include:

- app launches by double-click or command-line launch of the `.app`
- no browser required
- no terminal required
- main window opens into `首頁`
- grounded Ask still works
- `收件匣` import still works
- `Scan now` still works
- reflection / correction still work
- app shutdown does not leave orphan server processes
- shell build verification succeeds with the additive `packaging/macos/requirements-shell.txt` baseline installed

## 15. Definition Of Done

Phase 12 is done when:

- `Infinite Lore` can be launched as a macOS app
- the app opens a single main window
- the current Workbench V2 loads inside that shell
- the user does not need localhost or terminal to use it
- the existing vault workflow remains intact
- the key flows still work after packaging

## 16. References

- pywebview uses the native system web engine on macOS:
  - <https://pywebview.flowrl.com/guide/web_engine.html>
- pywebview supports freezing / distribution guidance:
  - <https://pywebview.flowrl.com/guide/freezing>
- PyInstaller documents macOS app bundle behavior:
  - <https://www.pyinstaller.org/en/stable/usage.html>
- Tauri sidecar and localhost references for the alternative path:
  - <https://tauri.app/develop/sidecar/>
  - <https://v2.tauri.app/plugin/localhost/>
