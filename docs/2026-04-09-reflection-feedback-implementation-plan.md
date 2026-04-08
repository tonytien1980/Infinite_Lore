# Reflection And Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Ask-integrated reflection and correction workflow so the user can immediately capture interpretation, propose knowledge corrections, confirm them inline, and keep Ask layered and traceable.

**Architecture:** The implementation adds a dedicated `reflection_service` to manage reflection drafts, correction proposals, archive snapshots, and confirmation flows. The Ask service remains the grounded source-of-truth answer layer, but it is extended to retrieve recent linked reflections as a second visible layer. The Workbench API exposes draft and confirm endpoints, while the Ask page grows a same-page `Respond Now` interaction zone with no modal or page transitions.

**Tech Stack:** Python 3.9, FastAPI, `unittest`, existing Workbench backend, existing Ask service, existing vault filesystem contracts, vanilla HTML/CSS/JavaScript

---

## File Structure

### Files to create

- `docs/2026-04-09-reflection-feedback-implementation-plan.md`
- `workbench/reflection_service.py`
- `tests/test_reflection_feedback.py`

### Files to modify

- `workbench/ask_service.py`
- `workbench/server.py`
- `workbench/static/index.html`
- `workbench/static/app.js`
- `00_System/Workflow Guide.md`
- `docs/2026-04-08-execution-roadmap.md`

### Runtime directories this plan will write into

- `50_Brainstorming/reflections/<domain>/`
- `50_Brainstorming/corrections/pending/<domain>/`
- `50_Brainstorming/corrections/applied/<domain>/`
- `50_Brainstorming/corrections/rejected/<domain>/`
- `80_Archive/wiki-versions/<domain>/`

## Task 1: Add Failing Backend Tests For Reflection And Correction Flows

**Files:**

- Create: `tests/test_reflection_feedback.py`

- [ ] **Step 1: Write the failing test file for reflection draft, reflection save, correction draft, correction apply, and Ask reflection layering**

Create `tests/test_reflection_feedback.py` with:

```python
import tempfile
import unittest
from pathlib import Path

from workbench.ask_service import answer_question
from workbench.reflection_service import (
    apply_correction,
    draft_correction,
    draft_reflection,
    save_reflection,
)


def write_note(path: Path, metadata: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata + "\n" + body, encoding="utf-8")


class ReflectionFeedbackTests(unittest.TestCase):
    def seed_vault(self, root: Path) -> str:
        note_path = root / "30_Wiki/ai-application/library-systems--synthesis.md"
        write_note(
            note_path,
            (
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n"
            ),
            (
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes knowledge into reusable access points.\n\n"
                "## Key Points\n"
                "- It supports retrieval.\n\n"
                "## Source Lineage\n"
                "- Raw bundle: `20_Raw/inbox/library`\n"
            ),
        )
        return note_path.relative_to(root).as_posix()

    def test_draft_reflection_selects_linked_note_and_preserves_raw_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            draft = draft_reflection(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="這讓我想到知識入口應該比知識量更重要。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )

            self.assertEqual(draft["linked_note_ref"], linked_note)
            self.assertEqual(draft["raw_input"], "這讓我想到知識入口應該比知識量更重要。")
            self.assertIn("My Interpretation", draft["body"])

    def test_save_reflection_writes_linked_entry_under_reflections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            draft = draft_reflection(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="知識入口比堆資料更重要。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )
            result = save_reflection(root, draft)

            saved_path = root / result["path"]
            self.assertTrue(saved_path.exists())
            self.assertIn("50_Brainstorming/reflections/ai-application/", result["path"])
            self.assertIn("raw_input:", saved_path.read_text(encoding="utf-8"))

    def test_draft_correction_returns_full_rewritten_note_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            proposal = draft_correction(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="請把 retrieval 改成 reusable access。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )

            self.assertEqual(proposal["target_note_ref"], linked_note)
            self.assertIn("# Library Systems", proposal["proposed_content"])
            self.assertIn("reusable", proposal["proposed_content"].lower())

    def test_apply_correction_archives_old_version_and_overwrites_live_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            proposal = draft_correction(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="請把 retrieval 改成 reusable access。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )
            proposal["proposed_content"] = (
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes reusable access points for knowledge.\n"
            )
            result = apply_correction(root, proposal)

            live_text = (root / linked_note).read_text(encoding="utf-8")
            self.assertIn("reusable access points", live_text)
            self.assertTrue((root / result["archive_version_ref"]).exists())
            self.assertIn("50_Brainstorming/corrections/applied/ai-application/", result["proposal_path"])

    def test_ask_response_returns_recent_reflections_as_separate_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            draft = draft_reflection(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="知識入口比堆資料更重要。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )
            save_reflection(root, draft)

            result = answer_question(
                vault_root=root,
                question="What is a library system?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("answer", result)
            self.assertIn("reflections", result)
            self.assertEqual(len(result["reflections"]), 1)
            self.assertEqual(result["reflections"][0]["linked_note_ref"], linked_note)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_reflection_feedback -v
```

Expected:

- failure because `workbench.reflection_service` does not exist yet
- or failure because `answer_question()` does not yet return `reflections`

## Task 2: Implement Reflection And Correction Backend Service

**Files:**

- Create: `workbench/reflection_service.py`

- [ ] **Step 1: Create the service module with filesystem helpers and frontmatter rendering**

Create `workbench/reflection_service.py` and start with:

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from tools.import_bundle import slugify
from tools.wiki_compile import parse_frontmatter


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def archive_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def render_frontmatter(metadata: Dict[str, object]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            formatted = ", ".join(f'"{item}"' for item in value)
            lines.append(f"{key}: [{formatted}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def read_note(vault_root: Path, relative_path: str) -> Dict[str, object]:
    note_path = vault_root / relative_path
    metadata, body = parse_frontmatter(note_path.read_text(encoding="utf-8"))
    return {"path": relative_path, "metadata": metadata, "body": body}
```

- [ ] **Step 2: Add reflection draft and save helpers**

Extend `workbench/reflection_service.py` with:

```python
def pick_primary_grounding_note(grounding: List[Dict[str, object]]) -> Dict[str, object]:
    if not grounding:
        raise ValueError("grounding is required")
    return grounding[0]


def draft_reflection(
    vault_root: Path,
    ask_question: str,
    ask_mode: str,
    raw_input: str,
    grounding: List[Dict[str, object]],
) -> Dict[str, object]:
    linked_note = pick_primary_grounding_note(grounding)
    created_at = now_timestamp()
    title = f"Reflection - {linked_note['title']}"
    body = (
        "# Reflection\n\n"
        "## Triggering Question\n"
        f"{ask_question}\n\n"
        "## My Interpretation\n"
        f"{raw_input}\n\n"
        "## Linked Context\n"
        f"- Linked note: `{linked_note['path']}`\n"
    )
    return {
        "id": f"reflection-{slugify(linked_note['title'])}-{archive_stamp()}",
        "title": title,
        "layer": "brainstorming",
        "note_type": "reflection-entry",
        "primary_domain": linked_note.get("primary_domain", "unclassified"),
        "related_domains": [],
        "privacy": "private",
        "status": "active",
        "created_at": created_at,
        "updated_at": created_at,
        "linked_note_ref": linked_note["path"],
        "linked_note_title": linked_note["title"],
        "ask_question": ask_question,
        "ask_mode": ask_mode,
        "grounding_note_refs": [item["path"] for item in grounding],
        "source_refs": [],
        "reflection_kind": "interpretation",
        "raw_input": raw_input,
        "body": body,
    }


def save_reflection(vault_root: Path, draft: Dict[str, object]) -> Dict[str, str]:
    domain = str(draft["primary_domain"])
    filename = f"{slugify(str(draft['linked_note_title']))}--reflection--{archive_stamp()}.md"
    relative_path = f"50_Brainstorming/reflections/{domain}/{filename}"
    absolute_path = vault_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {key: value for key, value in draft.items() if key != "body"}
    absolute_path.write_text(render_frontmatter(metadata) + "\n" + str(draft["body"]), encoding="utf-8")
    return {"path": relative_path}
```

- [ ] **Step 3: Add correction draft and apply helpers**

Extend `workbench/reflection_service.py` with:

```python
def draft_correction(
    vault_root: Path,
    ask_question: str,
    ask_mode: str,
    raw_input: str,
    grounding: List[Dict[str, object]],
) -> Dict[str, object]:
    target_note = pick_primary_grounding_note(grounding)
    note = read_note(vault_root, target_note["path"])
    created_at = now_timestamp()
    proposal_body = (
        "# Correction Proposal\n\n"
        "## Triggering Question\n"
        f"{ask_question}\n\n"
        "## Reported Issue\n"
        f"{raw_input}\n\n"
        "## Proposed Change\n"
        f"{note['body']}\n\n"
        "## Evidence\n"
        f"- Target note: `{target_note['path']}`\n"
    )
    return {
        "id": f"correction-{slugify(target_note['title'])}-{archive_stamp()}",
        "title": f"Correction Proposal - {target_note['title']}",
        "layer": "brainstorming",
        "note_type": "correction-proposal",
        "primary_domain": target_note.get("primary_domain", "unclassified"),
        "related_domains": [],
        "privacy": "private",
        "status": "pending",
        "created_at": created_at,
        "updated_at": created_at,
        "target_note_ref": target_note["path"],
        "target_note_title": target_note["title"],
        "ask_question": ask_question,
        "ask_mode": ask_mode,
        "grounding_note_refs": [item["path"] for item in grounding],
        "source_refs": [],
        "proposal_status": "pending",
        "proposal_kind": "correction",
        "archive_version_ref": "",
        "applied_at": "",
        "reported_issue": raw_input,
        "proposed_content": note["body"],
        "body": proposal_body,
    }


def apply_correction(vault_root: Path, proposal: Dict[str, object]) -> Dict[str, str]:
    target_path = vault_root / str(proposal["target_note_ref"])
    domain = str(proposal["primary_domain"])
    archive_name = f"{target_path.stem}--before-correction--{archive_stamp()}.md"
    archive_relative = f"80_Archive/wiki-versions/{domain}/{archive_name}"
    archive_path = vault_root / archive_relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")

    target_path.write_text(str(proposal["proposed_content"]), encoding="utf-8")

    proposal["proposal_status"] = "applied"
    proposal["status"] = "applied"
    proposal["archive_version_ref"] = archive_relative
    proposal["applied_at"] = now_timestamp()

    proposal_name = f"{slugify(str(proposal['target_note_title']))}--correction--{archive_stamp()}.md"
    proposal_relative = f"50_Brainstorming/corrections/applied/{domain}/{proposal_name}"
    proposal_path = vault_root / proposal_relative
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {key: value for key, value in proposal.items() if key not in {'body', 'proposed_content', 'reported_issue'}}
    body = (
        "# Correction Proposal\n\n"
        "## Triggering Question\n"
        f"{proposal['ask_question']}\n\n"
        "## Reported Issue\n"
        f"{proposal['reported_issue']}\n\n"
        "## Proposed Change\n"
        f"{proposal['proposed_content']}\n\n"
        "## Evidence\n"
        f"- Target note: `{proposal['target_note_ref']}`\n\n"
        "## Decision\n"
        "- applied\n"
    )
    proposal_path.write_text(render_frontmatter(metadata) + "\n" + body, encoding="utf-8")
    return {"archive_version_ref": archive_relative, "proposal_path": proposal_relative}
```

- [ ] **Step 4: Run backend service tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_reflection_feedback -v
```

Expected:

- all reflection and correction backend tests pass

## Task 3: Extend Ask Service To Return Reflections As A Separate Layer

**Files:**

- Modify: `workbench/ask_service.py`
- Test: `tests/test_reflection_feedback.py`

- [ ] **Step 1: Add recent reflection retrieval to Ask results**

Update `workbench/ask_service.py` to import the parser helpers and add:

```python
def retrieve_reflections(vault_root: Path, grounding: List[Dict[str, object]]) -> List[Dict[str, object]]:
    reflections_root = vault_root / "50_Brainstorming" / "reflections"
    if not reflections_root.exists() or not grounding:
        return []

    linked_paths = {note["path"] for note in grounding}
    matches = []
    for reflection_path in reflections_root.rglob("*.md"):
        metadata, body = read_note(reflection_path)
        linked_note_ref = str(metadata.get("linked_note_ref", ""))
        if linked_note_ref not in linked_paths:
            continue
        matches.append(
            {
                "path": reflection_path.relative_to(vault_root).as_posix(),
                "title": metadata.get("title", reflection_path.stem),
                "linked_note_ref": linked_note_ref,
                "created_at": metadata.get("created_at", ""),
                "body": body,
            }
        )

    matches.sort(key=lambda item: item["created_at"], reverse=True)
    return matches[:3]
```

- [ ] **Step 2: Return `reflections` in both Query and Ask responses**

Update `answer_question()` in `workbench/ask_service.py` so it computes:

```python
    reflections = retrieve_reflections(vault_root, grounding)
```

and returns `reflections` in every response payload:

```python
        return {
            "mode": "ask",
            "answer": answer,
            "grounding": grounding,
            "trace": trace,
            "reflections": reflections,
            "limits": limits,
            "answer_source": "local",
        }
```

Apply the same field to:

- query responses
- local ask responses
- model-backed ask responses

- [ ] **Step 3: Run the relevant tests and verify the Ask layer stays green**

Run:

```bash
python3 -m unittest tests.test_query_ask tests.test_reflection_feedback -v
```

Expected:

- Query / Ask tests still pass
- the reflection-layer Ask test now passes

## Task 4: Add Reflection And Correction API Endpoints

**Files:**

- Modify: `workbench/server.py`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add API endpoint tests for reflection and correction flows**

Append these tests to `tests/test_workbench_api.py`:

```python
    def test_reflection_endpoints_draft_and_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "30_Wiki/ai-application/library-systems--synthesis.md").write_text(
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes reusable access points.\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            draft = client.post(
                "/api/ask/reflection/draft",
                json={
                    "question": "What is a library system?",
                    "ask_mode": "ask",
                    "raw_input": "知識入口比堆資料更重要。",
                    "grounding": [
                        {
                            "path": "30_Wiki/ai-application/library-systems--synthesis.md",
                            "title": "Library Systems",
                            "primary_domain": "ai-application",
                        }
                    ],
                },
            )
            saved = client.post("/api/ask/reflection/confirm", json=draft.json())

            self.assertEqual(draft.status_code, 200)
            self.assertEqual(saved.status_code, 200)
            self.assertTrue((root / saved.json()["path"]).exists())

    def test_correction_endpoints_draft_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note_path = root / "30_Wiki/ai-application/library-systems--synthesis.md"
            note_path.parent.mkdir(parents=True)
            note_path.write_text(
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes retrieval.\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            draft = client.post(
                "/api/ask/correction/draft",
                json={
                    "question": "What is a library system?",
                    "ask_mode": "ask",
                    "raw_input": "請改成 reusable access points。",
                    "grounding": [
                        {
                            "path": "30_Wiki/ai-application/library-systems--synthesis.md",
                            "title": "Library Systems",
                            "primary_domain": "ai-application",
                        }
                    ],
                },
            )
            payload = draft.json()
            payload["proposed_content"] = (
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes reusable access points.\n"
            )
            applied = client.post("/api/ask/correction/apply", json=payload)

            self.assertEqual(draft.status_code, 200)
            self.assertEqual(applied.status_code, 200)
            self.assertIn("reusable access points", note_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- failure because the new Ask reflection/correction endpoints do not exist yet

- [ ] **Step 3: Add the reflection and correction endpoints**

Modify `workbench/server.py` to import the service helpers:

```python
from workbench.reflection_service import (
    apply_correction,
    draft_correction,
    draft_reflection,
    save_reflection,
)
```

Then add these routes:

```python
    @app.post("/api/ask/reflection/draft")
    def ask_reflection_draft(payload: dict) -> dict:
        return draft_reflection(
            vault_root=vault_root,
            ask_question=payload["question"],
            ask_mode=payload["ask_mode"],
            raw_input=payload["raw_input"],
            grounding=payload["grounding"],
        )

    @app.post("/api/ask/reflection/confirm")
    def ask_reflection_confirm(payload: dict) -> dict:
        return save_reflection(vault_root, payload)

    @app.post("/api/ask/correction/draft")
    def ask_correction_draft(payload: dict) -> dict:
        return draft_correction(
            vault_root=vault_root,
            ask_question=payload["question"],
            ask_mode=payload["ask_mode"],
            raw_input=payload["raw_input"],
            grounding=payload["grounding"],
        )

    @app.post("/api/ask/correction/apply")
    def ask_correction_apply(payload: dict) -> dict:
        return apply_correction(vault_root, payload)
```

- [ ] **Step 4: Run the API tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_workbench_api tests.test_reflection_feedback -v
```

Expected:

- all Workbench API tests pass
- new reflection/correction endpoint tests pass

## Task 5: Add Same-Page Ask Feedback UX

**Files:**

- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`

- [ ] **Step 1: Extend the Ask page layout with `Your Reflections` and `Respond Now`**

Update the Ask section in `workbench/static/index.html` so it contains:

```html
        <section class="page" data-page="ask">
          <div class="grid ask-layout">
            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">Library Answer</p>
                  <h3>Grounded response</h3>
                </div>
              </div>
              <div id="askAnswer" class="empty-state">
                Ask the library and the grounded answer will appear here.
              </div>
              <div id="askGrounding" class="list-stack empty-state">Grounding will appear here.</div>
              <div id="askTrace" class="list-stack empty-state">Source trace will appear here.</div>
              <div id="askLimits" class="list-stack empty-state">Limits and uncertainty will appear here when needed.</div>
            </section>

            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">Your Reflections</p>
                  <h3>Recent interpretation layer</h3>
                </div>
              </div>
              <div id="askReflections" class="list-stack empty-state">Recent reflections will appear here.</div>
              <button id="viewAllReflectionsButton" type="button" class="ghost-button">View all</button>
            </section>

            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">Respond Now</p>
                  <h3>Correct or interpret in place</h3>
                </div>
              </div>
              <form id="askFeedbackForm" class="stack-form">
                <label>
                  <span>Feedback</span>
                  <textarea id="askFeedbackInput" placeholder="Add a correction or your interpretation in the current Ask context."></textarea>
                </label>
                <div class="ask-actions">
                  <button type="button" id="draftCorrectionButton" class="secondary-button">Correct this knowledge</button>
                  <button type="button" id="draftReflectionButton" class="primary-button">Add my interpretation</button>
                </div>
              </form>
              <div id="feedbackEditor" class="empty-state">Drafted corrections or reflections will appear here for confirmation.</div>
            </section>
          </div>
        </section>
```

- [ ] **Step 2: Wire the Ask page to render reflections and handle draft / confirm flows**

Extend `workbench/static/app.js` with:

```javascript
state.askResult = null;

function renderReflections(reflections) {
  const box = document.getElementById("askReflections");
  box.innerHTML = "";
  (reflections || []).forEach((item) => {
    box.appendChild(createListItem(item.title, "reflection", item.linked_note_ref));
  });
  if (!box.children.length) box.textContent = "No reflections linked to this answer yet.";
}

function currentAskPayload() {
  return {
    question: document.getElementById("askInput").value,
    ask_mode: document.getElementById("askMode").value,
    grounding: state.askResult?.grounding || [],
  };
}
```

Then inside `runAsk(question, mode)` add:

```javascript
  state.askResult = payload;
  renderReflections(payload.reflections || []);
```

Add the reflection draft flow:

```javascript
async function draftReflection() {
  const payload = await fetchJson("/api/ask/reflection/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...currentAskPayload(),
      raw_input: document.getElementById("askFeedbackInput").value,
    }),
  });
  state.pendingFeedback = { type: "reflection", payload };
  document.getElementById("feedbackEditor").textContent = payload.body;
}
```

Add the correction draft flow:

```javascript
async function draftCorrection() {
  const payload = await fetchJson("/api/ask/correction/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...currentAskPayload(),
      raw_input: document.getElementById("askFeedbackInput").value,
    }),
  });
  state.pendingFeedback = { type: "correction", payload };
  document.getElementById("feedbackEditor").textContent = payload.proposed_content;
}
```

Add listeners:

```javascript
document.getElementById("draftReflectionButton").addEventListener("click", draftReflection);
document.getElementById("draftCorrectionButton").addEventListener("click", draftCorrection);
```

- [ ] **Step 3: Add confirm actions for reflection save and correction apply**

Still in `workbench/static/app.js`, add:

```javascript
async function confirmPendingFeedback() {
  if (!state.pendingFeedback) return;

  if (state.pendingFeedback.type === "reflection") {
    await fetchJson("/api/ask/reflection/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.pendingFeedback.payload),
    });
    await runAsk(document.getElementById("askInput").value, document.getElementById("askMode").value);
    return;
  }

  if (state.pendingFeedback.type === "correction") {
    state.pendingFeedback.payload.proposed_content = document.getElementById("feedbackEditor").textContent;
    await fetchJson("/api/ask/correction/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.pendingFeedback.payload),
    });
    await runAsk(document.getElementById("askInput").value, document.getElementById("askMode").value);
  }
}
```

Add a confirm button to the `feedbackEditor` markup or immediately below it:

```html
<div class="ask-actions">
  <button type="button" id="confirmFeedbackButton" class="primary-button">Confirm</button>
</div>
```

Then bind it:

```javascript
document.getElementById("confirmFeedbackButton").addEventListener("click", confirmPendingFeedback);
```

- [ ] **Step 4: Run the Workbench API tests to confirm the UI wiring did not break the app contract**

Run:

```bash
python3 -m unittest tests.test_workbench_api tests.test_query_ask tests.test_reflection_feedback -v
```

Expected:

- backend contract tests still pass after the frontend wiring assumptions

## Task 6: Sync Docs And Verify The Whole Reflection / Feedback Phase

**Files:**

- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`

- [ ] **Step 1: Update the workflow guide with Ask-integrated reflection behavior**

Append to `00_System/Workflow Guide.md`:

```md
## Reflection And Feedback

Use the Ask page as the primary reflection surface.

- `Correct this knowledge` generates a full correction proposal first.
- confirmed corrections archive the previous wiki version before applying.
- `Add my interpretation` creates a linked reflection entry.
- Ask responses continue to show `Library Answer` separately from `Your Reflections`.
```

- [ ] **Step 2: Mark the roadmap when the phase is actually complete**

Update `docs/2026-04-08-execution-roadmap.md` after implementation so:

- phase 6 is described as completed
- the next immediate phase becomes phase 7 automation / watcher

- [ ] **Step 3: Run the full regression suite**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_query_ask tests.test_reflection_feedback tests.test_health_check -v
python3 tools/health_check.py .
```

Expected:

- all tests pass
- `Vault health check passed`

- [ ] **Step 4: Run one live Workbench verification cycle**

Run:

```bash
python3 tools/run_workbench.py
```

Then verify with HTTP calls:

```bash
curl -s http://127.0.0.1:8765/api/system/info
curl -s -X POST http://127.0.0.1:8765/api/ask -H 'Content-Type: application/json' -d '{"question":"What is a library system?","mode":"ask"}'
```

Expected:

- Workbench starts successfully
- Ask still returns grounded output
- reflection endpoints are available for the next manual check

- [ ] **Step 5: Commit the phase**

Run:

```bash
git add \
  00_System/Workflow Guide.md \
  docs/2026-04-08-execution-roadmap.md \
  docs/2026-04-09-reflection-feedback-implementation-plan.md \
  workbench/reflection_service.py \
  workbench/ask_service.py \
  workbench/server.py \
  workbench/static/index.html \
  workbench/static/app.js \
  tests/test_reflection_feedback.py \
  tests/test_workbench_api.py
git commit -m "feat: add reflection feedback layer"
```

Expected:

- a clean commit containing the reflection / feedback phase

## Self-Review Checklist

- [ ] Spec coverage check: every interaction in `docs/2026-04-09-reflection-feedback-spec.md` maps to a task above
- [ ] Placeholder scan: no `TBD`, `TODO`, `implement later`, or empty code-step blocks
- [ ] Type consistency check:
  - `draft_reflection`
  - `save_reflection`
  - `draft_correction`
  - `apply_correction`
  - `reflections` Ask response field
  all use the same names across tests, service, API, and frontend
