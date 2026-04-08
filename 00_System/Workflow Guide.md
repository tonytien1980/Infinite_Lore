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
