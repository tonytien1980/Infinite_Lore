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

## Workbench UI

Run the local Workbench UI with:

```bash
python3 tools/run_workbench.py
```

Then open the local URL shown in the terminal.

## Ask And Query

Use the Workbench Ask page as the main knowledge entry surface.

- `Auto` is the default mode.
- `Ask` produces a grounded answer from compiled wiki notes.
- `Query` shows matching notes and source coverage without forcing a synthesized answer.

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
