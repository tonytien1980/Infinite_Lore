# Workflow Guide

## Knowledge-First Writing

1. Put new source material into `20_Raw/inbox/`.
2. Move processed raw items into `20_Raw/done/`.
3. Compile durable knowledge into `30_Wiki/`.
4. Explore article or output direction in `50_Brainstorming/`.
5. Draft final outputs in `70_Artifacts/`.

## Project-First Work

1. Open project status in `40_Projects/`.
2. Think in `thinking.md`.
3. Record progress in `log.md`.
4. Connect outputs to `70_Artifacts/`.

## Journal-First Reflection

1. Write in `60_Journal/daily/`.
2. Route useful insight into `wiki`, `projects`, or `artifacts`.
3. Create periodic synthesis in `60_Journal/weekly/`.

## Raw Import

Use the importer to normalize new source material into raw bundles and immediately compile it into wiki notes:

```bash
python3 tools/import_bundle.py --source <path-or-url> --domain <primary-domain>
```

This creates a raw bundle in `20_Raw/inbox/`, then automatically produces source-grounded wiki notes in `30_Wiki/<domain>/`.

The current importer now supports:

- text-first formats:
  - `txt`
  - `md`
  - `html`
  - web article captures
  - `docx`
  - `pdf`
- first-pass multimodal formats:
  - `pptx`
  - images:
    - `png`
    - `jpg`
    - `jpeg`
    - `webp`

Current multimodal behavior is intentionally bounded:

- `pptx` imports normalize slide text into `content.md`
- image imports use Apple Vision as the primary local OCR path on macOS
- when the local Vision helper is unavailable or fails, image imports keep the bounded structural summary path and still emit OCR-aware sections with warning-state content
- image imports write OCR-aware `content.md` sections:
  - `Source Summary`
  - `Structural Summary`
  - `OCR Summary`
  - `OCR Text`
  - `Screenshot Signals`
  - `Extraction Notes`
- image bundles record OCR metadata:
  - `ocr_engine`
  - `ocr_attempted`
  - `ocr_status`
  - `ocr_text_present`
  - `image_interpretation_mode`
  - `image_kind_guess`
- image imports stay `review_required: true`
- the original source file is still preserved inside the raw bundle

## Workbench UI

Run the local Workbench UI with:

```bash
python3 tools/run_workbench.py
```

Then open the local URL shown in the terminal.

The shipped Workbench V2 shell is organized as:

- `首頁` as the 提問工作台 and main working surface
- `摘要` as the former dashboard-like overview page
- Traditional Chinese as the primary navigation and control language
- a top / middle / bottom homepage layout
- a desktop-first shell posture that already assumes a windowed work surface, even before packaging as a desktop app
- follow-up controls on `首頁` stay disabled until the answer has grounded note evidence

## macOS App Shell

Run the local desktop shell from source with:

```bash
python3 tools/run_macos_app.py
```

Build the packaged macOS app with:

```bash
tools/build_macos_app.sh
```

The first delivered macOS app shell currently provides:

- a single main window
- hidden localhost and no required browser tab
- automatic embedded server startup and shutdown
- the same shared vault workflow as the browser Workbench
- a Traditional Chinese loading state before the Workbench is ready
- a Traditional Chinese recovery view with retry / choose-vault / quit actions when shell launch fails

Current local-build behavior:

- the packaged `.app` auto-resolves the vault root when it is launched from the local build output under `<vault>/dist/Infinite Lore.app`
- if that bundle is moved away from the local build layout, the shell next reuses the last confirmed vault root when available
- if automatic resolution still fails, the shell opens a `選擇知識庫資料夾` picker and remembers the confirmed vault for later launches

Shell build baseline note:

- `packaging/macos/requirements-shell.txt` is the verified additive dependency baseline for the macOS shell and build flow
- it exists to install the shell-specific `pywebview` / `PyInstaller` / PyObjC requirements used by `tools/build_macos_app.sh`
- it is not a full project bootstrap replacement for the main Infinite Lore Python environment

## Automation And Scan Now

Use the Workbench `Inbox` for practical automation.

- Configure explicit sources inside Inbox.
- `Scan now` persists the current Inbox source list before the scan starts.
- Each scan processes:
  - local intake
  - configured `rss-feed` sources
  - configured `article-list-page` sources
- The scan deduplicates candidates before running `import + compile`.
- Failed items remain visible for later retries.
- Configured-article retries stay bounded:
  - immediate repeat scans stay blocked after exhaustion
  - later manual scans can retry again after cooldown
  - stale configured-article failures are cleared when a source is removed, disabled, or a successful source scan no longer returns that article
- Inbox shows the latest scan summary so the user can quickly see discovered candidates, imports, compiles, failures, and exhausted retry state.

## Ask And Query

Use `首頁` as the main knowledge entry surface.

- `Auto` is the default mode.
- `Ask` produces a grounded answer from compiled wiki notes.
- `Query` shows matching notes and source coverage without forcing a synthesized answer.
- `Ask` now expands from lexical anchors through bounded relation edges:
  - `derived-from`
  - `shares-source`
- relation expansion stays supplemental:
  - no lexical anchor means no relation-driven answer
  - insufficient evidence still produces abstention instead of a guessed answer
- Ask results now show:
  - note grounding
  - source trace
  - relation trace when extra notes were pulled in through note links
- multimodal intake is now available at the importer layer, but the Ask layer is still relation-first rather than image-understanding-first.
- The homepage layout is vertical:
  - top: compact prompt bar
  - middle: main answer surface
  - bottom: evidence and follow-up work
- `摘要` is the operational overview page that carries the old dashboard-style content.
- Primary navigation is in Traditional Chinese.

The Query / Ask layer serves the library, not the open internet.

- Answers should come from `30_Wiki/` first.
- Raw bundles are used for trace, not as the first answer layer.
- If evidence is insufficient, the system should say so instead of inventing an answer.

## Reflection And Feedback

在同一個提問頁面上完成輕量的修正與個人詮釋，不要另外切走。

- 保持 `圖書館答案` 和 `你的反思` 分開顯示。
- 頁面上預設顯示最近 `3` 筆已連結的反思，必要時再用 `查看全部` 展開。
- 用同一個輸入框支援 `起草修正` 與 `起草反思`。
- 草稿留在同一頁面 inline 審閱，確認前都可以直接修改。
- 修正必須先確認才會套用，套用後首頁答案應可立即重新整理。
