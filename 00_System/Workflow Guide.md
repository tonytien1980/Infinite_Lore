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

Use the Workbench Ask page as the main knowledge entry surface.

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

The Query / Ask layer serves the library, not the open internet.

- Answers should come from `30_Wiki/` first.
- Raw bundles are used for trace, not as the first answer layer.
- If evidence is insufficient, the system should say so instead of inventing an answer.

## Reflection And Feedback

Use the same Ask page for lightweight correction and interpretation after the library answers.

- Keep `Library Answer` separate from `Your Reflections`.
- Show the latest `3` linked reflections on the page, with a `View all` control for the full set.
- Use `Respond Now` with one shared input for either `Correct this knowledge` or `Add my interpretation`.
- Drafts stay inline on the same page so the user can review and edit them before confirmation.
- A correction must be confirmed before it applies, and the Ask answer should be ready to refresh immediately after the apply step.
