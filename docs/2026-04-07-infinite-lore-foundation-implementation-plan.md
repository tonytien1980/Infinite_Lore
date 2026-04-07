# Infinite Lore Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable Infinite Lore vault foundation: core folder structure, system notes, domain entry notes, note templates, and a runnable health-check tool.

**Architecture:** The implementation keeps Obsidian as the primary working surface and stores system behavior in durable vault structure plus lightweight Python tooling. Documentation and templates define the human-and-AI operating model, while a small health checker verifies the most critical metadata and lineage rules from the specification.

**Tech Stack:** Markdown, YAML frontmatter conventions, Python 3.9 standard library, `unittest`, Git

---

## File Structure

### Files to create

- `.gitignore`
- `00_System/Home.md`
- `00_System/Domain Map.md`
- `00_System/Operating Principles.md`
- `00_System/Schema.md`
- `00_System/Workflow Guide.md`
- `00_System/Health Rules.md`
- `00_System/Template - Raw Metadata.md`
- `00_System/Template - Wiki Note.md`
- `00_System/Template - Project Status.md`
- `00_System/Template - Project Thinking.md`
- `00_System/Template - Project Log.md`
- `00_System/Template - Brainstorming Note.md`
- `00_System/Template - Journal Entry.md`
- `00_System/Template - Artifact.md`
- `10_Domains/business-strategy/index.md`
- `10_Domains/management/index.md`
- `10_Domains/marketing-acquisition/index.md`
- `10_Domains/finance-investing/index.md`
- `10_Domains/ai-application/index.md`
- `10_Domains/consulting/index.md`
- `10_Domains/personal/index.md`
- `20_Raw/inbox/.gitkeep`
- `20_Raw/done/business-strategy/.gitkeep`
- `20_Raw/done/management/.gitkeep`
- `20_Raw/done/marketing-acquisition/.gitkeep`
- `20_Raw/done/finance-investing/.gitkeep`
- `20_Raw/done/ai-application/.gitkeep`
- `20_Raw/done/consulting/.gitkeep`
- `20_Raw/done/personal/.gitkeep`
- `30_Wiki/business-strategy/.gitkeep`
- `30_Wiki/management/.gitkeep`
- `30_Wiki/marketing-acquisition/.gitkeep`
- `30_Wiki/finance-investing/.gitkeep`
- `30_Wiki/ai-application/.gitkeep`
- `30_Wiki/consulting/.gitkeep`
- `30_Wiki/personal/.gitkeep`
- `30_Wiki/shared/.gitkeep`
- `40_Projects/active/.gitkeep`
- `40_Projects/paused/.gitkeep`
- `40_Projects/completed/.gitkeep`
- `40_Projects/clients/.gitkeep`
- `50_Brainstorming/by-domain/.gitkeep`
- `50_Brainstorming/by-project/.gitkeep`
- `50_Brainstorming/by-artifact/.gitkeep`
- `50_Brainstorming/sessions/.gitkeep`
- `60_Journal/daily/.gitkeep`
- `60_Journal/weekly/.gitkeep`
- `60_Journal/life-themes/.gitkeep`
- `70_Artifacts/social/.gitkeep`
- `70_Artifacts/consulting/.gitkeep`
- `70_Artifacts/research/.gitkeep`
- `70_Artifacts/courses/.gitkeep`
- `70_Artifacts/books/.gitkeep`
- `80_Archive/.gitkeep`
- `90_Assets/.gitkeep`
- `tools/health_check.py`
- `tests/test_health_check.py`

### Files to modify

- `docs/2026-04-07-infinite-lore-system-spec.md`
  - only if implementation details require a small alignment fix discovered during execution

## Task 1: Create Repository Guardrails And Vault Skeleton

**Files:**

- Create: `.gitignore`
- Create: all `.gitkeep` paths listed above

- [ ] **Step 1: Write `.gitignore` for vault and Python working files**

```gitignore
.DS_Store
.worktrees/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.venv/
```

- [ ] **Step 2: Create the vault directories and placeholder keep files**

Run:

```bash
mkdir -p \
  00_System \
  10_Domains/business-strategy \
  10_Domains/management \
  10_Domains/marketing-acquisition \
  10_Domains/finance-investing \
  10_Domains/ai-application \
  10_Domains/consulting \
  10_Domains/personal \
  20_Raw/inbox \
  20_Raw/done/business-strategy \
  20_Raw/done/management \
  20_Raw/done/marketing-acquisition \
  20_Raw/done/finance-investing \
  20_Raw/done/ai-application \
  20_Raw/done/consulting \
  20_Raw/done/personal \
  30_Wiki/business-strategy \
  30_Wiki/management \
  30_Wiki/marketing-acquisition \
  30_Wiki/finance-investing \
  30_Wiki/ai-application \
  30_Wiki/consulting \
  30_Wiki/personal \
  30_Wiki/shared \
  40_Projects/active \
  40_Projects/paused \
  40_Projects/completed \
  40_Projects/clients \
  50_Brainstorming/by-domain \
  50_Brainstorming/by-project \
  50_Brainstorming/by-artifact \
  50_Brainstorming/sessions \
  60_Journal/daily \
  60_Journal/weekly \
  60_Journal/life-themes \
  70_Artifacts/social \
  70_Artifacts/consulting \
  70_Artifacts/research \
  70_Artifacts/courses \
  70_Artifacts/books \
  80_Archive \
  90_Assets \
  tools \
  tests
```

Then create the placeholder files:

```bash
touch \
  20_Raw/inbox/.gitkeep \
  20_Raw/done/business-strategy/.gitkeep \
  20_Raw/done/management/.gitkeep \
  20_Raw/done/marketing-acquisition/.gitkeep \
  20_Raw/done/finance-investing/.gitkeep \
  20_Raw/done/ai-application/.gitkeep \
  20_Raw/done/consulting/.gitkeep \
  20_Raw/done/personal/.gitkeep \
  30_Wiki/business-strategy/.gitkeep \
  30_Wiki/management/.gitkeep \
  30_Wiki/marketing-acquisition/.gitkeep \
  30_Wiki/finance-investing/.gitkeep \
  30_Wiki/ai-application/.gitkeep \
  30_Wiki/consulting/.gitkeep \
  30_Wiki/personal/.gitkeep \
  30_Wiki/shared/.gitkeep \
  40_Projects/active/.gitkeep \
  40_Projects/paused/.gitkeep \
  40_Projects/completed/.gitkeep \
  40_Projects/clients/.gitkeep \
  50_Brainstorming/by-domain/.gitkeep \
  50_Brainstorming/by-project/.gitkeep \
  50_Brainstorming/by-artifact/.gitkeep \
  50_Brainstorming/sessions/.gitkeep \
  60_Journal/daily/.gitkeep \
  60_Journal/weekly/.gitkeep \
  60_Journal/life-themes/.gitkeep \
  70_Artifacts/social/.gitkeep \
  70_Artifacts/consulting/.gitkeep \
  70_Artifacts/research/.gitkeep \
  70_Artifacts/courses/.gitkeep \
  70_Artifacts/books/.gitkeep \
  80_Archive/.gitkeep \
  90_Assets/.gitkeep
```

- [ ] **Step 3: Verify the vault skeleton exists**

Run:

```bash
rg --files .
```

Expected:

- output includes the new top-level system note paths
- output includes `.gitkeep` placeholders across the major system layers

## Task 2: Create System Notes, Domain Entry Notes, And Note Templates

**Files:**

- Create: `00_System/Home.md`
- Create: `00_System/Domain Map.md`
- Create: `00_System/Operating Principles.md`
- Create: `00_System/Schema.md`
- Create: `00_System/Workflow Guide.md`
- Create: `00_System/Health Rules.md`
- Create: all seven `10_Domains/*/index.md`
- Create: all seven template notes in `00_System/`

- [ ] **Step 1: Create `00_System/Home.md`**

```md
# Infinite Lore Home

## System Entry

- [[00_System/Domain Map]]
- [[00_System/Operating Principles]]
- [[00_System/Schema]]
- [[00_System/Workflow Guide]]
- [[00_System/Health Rules]]

## Domains

- [[10_Domains/business-strategy/index|Business Strategy]]
- [[10_Domains/management/index|Management]]
- [[10_Domains/marketing-acquisition/index|Marketing Acquisition]]
- [[10_Domains/finance-investing/index|Finance Investing]]
- [[10_Domains/ai-application/index|AI Application]]
- [[10_Domains/consulting/index|Consulting]]
- [[10_Domains/personal/index|Personal]]

## Main Working Lanes

- Raw intake: `20_Raw/inbox/`
- Maintained knowledge: `30_Wiki/`
- Active projects: `40_Projects/`
- Exploration and writing prep: `50_Brainstorming/`
- Journal and life themes: `60_Journal/`
- Outputs: `70_Artifacts/`
```

- [ ] **Step 2: Create the core system notes**

Use these note bodies:

`00_System/Domain Map.md`

```md
# Domain Map

## Top-Level Domains

- business-strategy
- management
- marketing-acquisition
- finance-investing
- ai-application
- consulting
- personal

## Rules

- Every formal note must have one `primary_domain`.
- Notes may have multiple `related_domains`.
- Domains may evolve over time through split, merge, or rename.
- Cross-domain notes should be linked, not duplicated.
```

`00_System/Operating Principles.md`

```md
# Operating Principles

- Preserve raw sources.
- Keep lineage from source to knowledge to output.
- Treat brainstorming as exploratory, not canonical.
- Use domain-first navigation for reading and daily work.
- Prefer adding structured notes over overwriting important ones.
- Let the vault stay useful even if journaling is light or absent.
```

`00_System/Schema.md`

```md
# Schema

## Core Frontmatter

```yaml
id:
title:
layer:
note_type:
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
```

## Privacy Levels

- `private`
- `publishable`
- `client-confidential`
```

`00_System/Workflow Guide.md`

```md
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
```

`00_System/Health Rules.md`

```md
# Health Rules

## Check For

- notes missing `primary_domain`
- wiki or artifact notes missing `source_refs`
- confidential notes incorrectly marked as publishable
- stale or isolated wiki notes
- broken raw-to-wiki lineage
- broken wiki-to-artifact lineage
```

- [ ] **Step 3: Create one reusable domain index pattern and apply it to all seven domains**

Use this structure for each `10_Domains/<domain>/index.md`:

```md
---
title: <Display Name>
layer: domain-index
primary_domain: <domain-id>
related_domains: []
privacy: private
status: active
created_at: 2026-04-07
updated_at: 2026-04-07
source_refs: []
---

# <Display Name>

## Fixed Navigation

- Core knowledge: `30_Wiki/<domain-id>/`
- Raw intake: `20_Raw/done/<domain-id>/`
- Brainstorming: `50_Brainstorming/by-domain/`
- Outputs: `70_Artifacts/`

## What To Review

- New raw sources to process
- Existing knowledge to refine
- Topics worth turning into writing
- Related active projects
- Cross-domain connections
```

Apply the display names:

- Business Strategy
- Management
- Marketing Acquisition
- Finance Investing
- AI Application
- Consulting
- Personal

- [ ] **Step 4: Create note templates for every formal layer**

Use these exact template headers:

`00_System/Template - Raw Metadata.md`

```md
---
source_type:
source_title:
source_ref:
imported_at:
source_created_at:
published_at:
primary_domain:
related_domains: []
privacy:
content_hash:
status:
---

# Raw Metadata
```

`00_System/Template - Wiki Note.md`

```md
---
id:
title:
layer: wiki
note_type:
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
confidence:
last_compiled_at:
last_reviewed_at:
---

# Title

## Summary

## Core Idea

## Linked Notes

## Source Lineage
```

`00_System/Template - Project Status.md`

```md
---
id:
title:
layer: project
note_type: project-status
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
---

# Project Status

## Objective

## Current State

## Next Actions

## Risks
```

`00_System/Template - Project Thinking.md`

```md
---
id:
title:
layer: project
note_type: project-thinking
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
---

# Project Thinking

## Current Question

## Decomposition

## Hypotheses

## Open Loops
```

`00_System/Template - Project Log.md`

```md
---
id:
title:
layer: project
note_type: project-log
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
---

# Project Log
```

`00_System/Template - Brainstorming Note.md`

```md
---
id:
title:
layer: brainstorming
note_type: brainstorming
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
---

# Brainstorming

## Prompt

## Exploration

## Candidate Directions

## Promote Later
```

`00_System/Template - Journal Entry.md`

```md
---
id:
title:
layer: journal
note_type: journal-entry
primary_domain: personal
related_domains: []
privacy: private
status: active
created_at:
updated_at:
source_refs: []
energy:
mood:
sleep:
---

# Journal Entry
```

`00_System/Template - Artifact.md`

```md
---
id:
title:
layer: artifact
note_type:
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []
artifact_type:
audience:
goal:
linked_wiki: []
linked_brainstorming: []
stage:
---

# Artifact

## Brief

## Outline

## Draft
```

- [ ] **Step 5: Verify the Markdown skeleton files exist**

Run:

```bash
rg --files 00_System 10_Domains
```

Expected:

- output lists all system notes
- output lists all domain index notes
- output lists all template notes

## Task 3: Build Health Check With TDD

**Files:**

- Create: `tests/test_health_check.py`
- Create: `tools/health_check.py`

- [ ] **Step 1: Write the failing tests first**

Create `tests/test_health_check.py` with:

```python
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.health_check import check_vault


class HealthCheckTests(unittest.TestCase):
    def write(self, root: Path, relative_path: str, content: str) -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_accepts_valid_wiki_note_with_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "30_Wiki/ai-application/test.md",
                """
                ---
                title: Test
                layer: wiki
                note_type: concept
                primary_domain: ai-application
                related_domains: []
                privacy: private
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                source_refs:
                  - raw/test
                ---
                # Test
                """,
            )
            report = check_vault(root)
            self.assertEqual(report["errors"], [])

    def test_flags_formal_note_missing_primary_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "30_Wiki/shared/missing-domain.md",
                """
                ---
                title: Missing Domain
                layer: wiki
                note_type: concept
                related_domains: []
                privacy: private
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                source_refs:
                  - raw/test
                ---
                # Missing Domain
                """,
            )
            report = check_vault(root)
            self.assertIn("30_Wiki/shared/missing-domain.md: missing primary_domain", report["errors"])

    def test_flags_wiki_note_missing_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "30_Wiki/business-strategy/no-source.md",
                """
                ---
                title: No Source
                layer: wiki
                note_type: concept
                primary_domain: business-strategy
                related_domains: []
                privacy: private
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                ---
                # No Source
                """,
            )
            report = check_vault(root)
            self.assertIn("30_Wiki/business-strategy/no-source.md: missing source_refs", report["errors"])

    def test_flags_confidential_note_marked_publishable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "40_Projects/clients/acme/status.md",
                """
                ---
                title: ACME
                layer: project
                note_type: project-status
                primary_domain: consulting
                related_domains: []
                privacy: publishable
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                source_refs: []
                ---
                # ACME
                """,
            )
            report = check_vault(root)
            self.assertIn(
                "40_Projects/clients/acme/status.md: client path must use privacy client-confidential",
                report["errors"],
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_health_check -v
```

Expected:

- failure because `tools.health_check` does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Create `tools/health_check.py` with:

```python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List


FORMAL_LAYER_PREFIXES = (
    "10_Domains/",
    "30_Wiki/",
    "40_Projects/",
    "50_Brainstorming/",
    "60_Journal/",
    "70_Artifacts/",
)

SOURCE_REF_REQUIRED_PREFIXES = (
    "30_Wiki/",
    "70_Artifacts/",
)


def parse_frontmatter(text: str) -> Dict[str, object]:
    if not text.startswith("---\n"):
        return {}

    lines = text.splitlines()
    data: Dict[str, object] = {}
    key = None
    in_list = False

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("  - ") and key and in_list:
            data.setdefault(key, [])
            data[key].append(line[4:].strip())
            continue
        if ":" in line:
            raw_key, raw_value = line.split(":", 1)
            key = raw_key.strip()
            value = raw_value.strip()
            if value == "[]":
                data[key] = []
                in_list = False
            elif value == "":
                data[key] = []
                in_list = True
            else:
                data[key] = value
                in_list = False
    return data


def should_check_formal_note(relative_path: str) -> bool:
    return relative_path.endswith(".md") and relative_path.startswith(FORMAL_LAYER_PREFIXES)


def check_note(relative_path: str, metadata: Dict[str, object]) -> List[str]:
    errors: List[str] = []

    if "primary_domain" not in metadata or metadata.get("primary_domain") in ("", []):
        errors.append(f"{relative_path}: missing primary_domain")

    if relative_path.startswith(SOURCE_REF_REQUIRED_PREFIXES):
        source_refs = metadata.get("source_refs", [])
        if not source_refs:
            errors.append(f"{relative_path}: missing source_refs")

    if relative_path.startswith("40_Projects/clients/"):
        privacy = metadata.get("privacy")
        if privacy != "client-confidential":
            errors.append(f"{relative_path}: client path must use privacy client-confidential")

    return errors


def check_vault(root: Path) -> Dict[str, List[str]]:
    errors: List[str] = []

    for path in sorted(root.rglob("*.md")):
        relative_path = path.relative_to(root).as_posix()
        if not should_check_formal_note(relative_path):
            continue
        metadata = parse_frontmatter(path.read_text(encoding="utf-8"))
        errors.extend(check_note(relative_path, metadata))

    return {"errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Infinite Lore vault health.")
    parser.add_argument("root", nargs="?", default=".", help="Vault root path")
    args = parser.parse_args()

    report = check_vault(Path(args.root))
    if report["errors"]:
        for error in report["errors"]:
            print(error)
        return 1

    print("Vault health check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_health_check -v
```

Expected:

- all 4 tests pass

- [ ] **Step 5: Run the health checker on the real vault**

Run:

```bash
python3 tools/health_check.py .
```

Expected:

- either `Vault health check passed`
- or a concrete list of metadata issues to fix immediately

## Task 4: Align Real Notes With The Health Checker

**Files:**

- Modify: all formal `.md` notes created in Task 2 as needed

- [ ] **Step 1: Add frontmatter to formal notes where needed**

Use this header pattern for any formal note missing metadata:

```yaml
---
title:
layer:
note_type:
primary_domain:
related_domains: []
privacy: private
status: active
created_at: 2026-04-07
updated_at: 2026-04-07
source_refs: []
---
```

- [ ] **Step 2: Re-run the health checker until the real vault is clean**

Run:

```bash
python3 tools/health_check.py .
```

Expected:

- `Vault health check passed`

- [ ] **Step 3: Verify the implementation scope matches the specification**

Run:

```bash
rg --files . && python3 -m unittest tests.test_health_check -v && python3 tools/health_check.py .
```

Expected:

- repository includes the vault skeleton
- tests pass
- health check passes on the real repository
