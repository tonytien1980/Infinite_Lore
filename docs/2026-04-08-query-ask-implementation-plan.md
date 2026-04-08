# Query And Ask Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first grounded Query / Ask layer inside the Workbench so the user can ask the library a question, get a source-grounded answer or discovery result, and see where the answer came from.

**Architecture:** The implementation adds a retrieval-and-answer service to the Workbench backend. Query mode stays local and retrieval-driven. Ask mode first retrieves relevant wiki notes locally, then either uses a configured model route for answer synthesis or falls back to a deterministic local grounded summary when no provider is configured. The frontend reuses the existing single Ask input and adds auto-mode routing, result rendering, grounding, and trace display.

**Tech Stack:** Python 3.9, FastAPI, `unittest`, OpenAI Python SDK 2.x, existing Workbench services, existing wiki note corpus, vanilla HTML/CSS/JavaScript

---

## File Structure

### Files to create

- `docs/2026-04-08-query-ask-implementation-plan.md`
- `workbench/ask_service.py`
- `tests/test_query_ask.py`

### Files to modify

- `requirements.txt`
- `workbench/config_store.py`
- `workbench/server.py`
- `workbench/static/index.html`
- `workbench/static/app.js`
- `docs/2026-04-08-execution-roadmap.md`

## Task 1: Add Query / Ask Runtime Dependency And Settings Defaults

**Files:**

- Modify: `requirements.txt`
- Modify: `workbench/config_store.py`

- [ ] **Step 1: Add the OpenAI SDK to project dependencies**

Replace `requirements.txt` with:

```txt
pypdf>=6.9,<7
fastapi>=0.116,<1
uvicorn>=0.35,<1
httpx>=0.28,<1
python-multipart>=0.0.20,<1
openai>=2.30,<3
```

- [ ] **Step 2: Extend config defaults for Ask routing**

Update `workbench/config_store.py` so the default config includes:

```python
DEFAULT_CONFIG = {
    "providers": [],
    "routes": {
        "scan": "no_model",
        "import": "no_model",
        "compile": "balanced",
        "ask": "best_deep",
        "query": "no_model",
        "reflection": "balanced",
    },
}
```

- [ ] **Step 3: Verify the dependency and config changes are present**

Run:

```bash
sed -n '1,120p' requirements.txt
sed -n '1,200p' workbench/config_store.py
```

Expected:

- `openai>=2.30,<3` is present
- config defaults include `query`

## Task 2: Write Failing Query / Ask Tests

**Files:**

- Create: `tests/test_query_ask.py`

- [ ] **Step 1: Write tests for intent routing, local query retrieval, grounded ask, and settings-based model routing**

Create `tests/test_query_ask.py` with:

```python
import tempfile
import unittest
from pathlib import Path

from workbench.ask_service import (
    infer_mode,
    answer_question,
)


def write_note(path: Path, metadata: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata + "\n" + body, encoding="utf-8")


class QueryAskTests(unittest.TestCase):
    def seed_vault(self, root: Path) -> None:
        write_note(
            root / "30_Wiki/ai-application/library-systems--synthesis.md",
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
                "- It helps retrieval.\n"
                "- It supports grounded answers.\n\n"
                "## Source Lineage\n"
                "- Raw bundle: `20_Raw/inbox/library`\n"
            ),
        )
        write_note(
            root / "30_Wiki/ai-application/library-systems--concept--knowledge-compilation.md",
            (
                "---\n"
                "title: Knowledge Compilation\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n"
            ),
            (
                "# Knowledge Compilation\n\n"
                "## Definition\n"
                "Knowledge compilation turns raw material into reusable notes.\n\n"
                "## Source Lineage\n"
                "- Raw bundle: `20_Raw/inbox/library`\n"
            ),
        )

    def test_infer_mode_prefers_query_for_listing_language(self) -> None:
        self.assertEqual(infer_mode("What notes do I have about library systems?", "auto"), "query")

    def test_infer_mode_prefers_ask_for_summary_language(self) -> None:
        self.assertEqual(infer_mode("Summarize what my library knows about library systems.", "auto"), "ask")

    def test_query_mode_returns_note_matches_without_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="What notes do I have about library systems?",
                requested_mode="query",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertEqual(result["mode"], "query")
            self.assertEqual(result["answer"], "")
            self.assertGreaterEqual(len(result["grounding"]), 1)

    def test_ask_mode_returns_grounded_local_answer_when_no_provider_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="What is knowledge compilation?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertEqual(result["mode"], "ask")
            self.assertIn("Knowledge compilation", result["answer"])
            self.assertGreaterEqual(len(result["grounding"]), 1)
            self.assertGreaterEqual(len(result["trace"]), 1)

    def test_ask_mode_uses_provider_route_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            def fake_generate(**kwargs):
                return "MODEL ANSWER"

            result = answer_question(
                vault_root=root,
                question="What is knowledge compilation?",
                requested_mode="ask",
                settings={
                    "providers": [
                        {
                            "provider": "openai",
                            "api_key": "sk-test",
                            "models": [{"id": "gpt-best", "role": "best_deep"}],
                        }
                    ],
                    "routes": {"query": "no_model", "ask": "best_deep"},
                },
                generate_answer=fake_generate,
            )

            self.assertEqual(result["answer"], "MODEL ANSWER")
            self.assertEqual(result["answer_source"], "model")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_query_ask -v
```

Expected:

- failure because `workbench.ask_service` does not exist yet

## Task 3: Implement Retrieval, Routing, And Grounded Answering

**Files:**

- Create: `workbench/ask_service.py`

- [ ] **Step 1: Create `workbench/ask_service.py`**

Create the module with:

- `infer_mode(question: str, requested_mode: str) -> str`
- local note indexing over `30_Wiki/`
- retrieval helpers for synthesis-first ranking
- `answer_question(...) -> dict`
- local fallback answer generator when no model provider is configured
- optional model-backed answer generation for configured providers

The module should support:

- single-input auto routing
- Query mode returning note matches without model use
- Ask mode returning:
  - `answer`
  - `grounding`
  - `trace`
  - `limits`
  - `mode`
  - `answer_source`

- OpenAI-backed answer generation using the current Python SDK Responses API when:
  - a provider exists
  - an API key exists
  - a model is mapped to the active role

- [ ] **Step 2: Use a deterministic local fallback answer generator**

The local fallback must:

- never pretend to be a model answer
- summarize directly from retrieved wiki note text
- clearly surface limits when evidence is weak

- [ ] **Step 3: Run the tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_query_ask -v
```

Expected:

- all 5 tests pass

## Task 4: Expose Query / Ask Through The Workbench API

**Files:**

- Modify: `workbench/server.py`

- [ ] **Step 1: Add a new Ask endpoint**

Add:

- `POST /api/ask`

Accepted JSON body:

```json
{
  "question": "...",
  "mode": "auto"
}
```

Returned JSON:

```json
{
  "mode": "ask",
  "answer": "...",
  "grounding": [],
  "trace": [],
  "limits": [],
  "answer_source": "model"
}
```

- [ ] **Step 2: Ensure the endpoint reads current local settings**

The endpoint must:

- load the local config
- honor the route mapping
- avoid model calls in Query mode by default

- [ ] **Step 3: Re-run Workbench API tests and Query/Ask tests**

Run:

```bash
python3 -m unittest tests.test_workbench_api tests.test_query_ask -v
```

Expected:

- all tests pass

## Task 5: Connect The Ask UI

**Files:**

- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`

- [ ] **Step 1: Add explicit Ask mode controls to the UI**

The Ask page should include:

- one input
- mode selector:
  - `Auto`
  - `Ask`
  - `Query`

- [ ] **Step 2: Wire the Ask form to `/api/ask`**

Update the frontend so the Ask page:

- posts the question and selected mode
- renders the answer
- renders the grounding list
- renders the source trace
- renders the limits section when present

- [ ] **Step 3: Update the home-page Ask shortcut to feed the main Ask page**

The Home page Ask box should:

- transfer the prompt into the Ask page
- keep the default mode on `Auto`
- trigger the Ask page request

- [ ] **Step 4: Verify the static files still exist and load**

Run:

```bash
rg --files workbench/static
```

Expected:

- static files remain present

## Task 6: Manual Verification

**Files:**

- Verify end-to-end behavior with the local Workbench

- [ ] **Step 1: Start the Workbench**

Run:

```bash
python3 tools/run_workbench.py
```

Expected:

- Workbench starts on `http://127.0.0.1:8765`

- [ ] **Step 2: Verify Ask mode manually**

Check in the browser:

- `Auto` mode exists
- `Ask` mode exists
- `Query` mode exists
- a question produces a structured result
- grounding and trace appear
- limits appear when evidence is weak

- [ ] **Step 3: Verify the API directly**

Run:

```bash
curl -s -X POST http://127.0.0.1:8765/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What does my library know about knowledge compilation?","mode":"auto"}'
```

Expected:

- JSON response contains `mode`
- JSON response contains `grounding`
- JSON response contains `trace`
- JSON response contains either a grounded answer or an explicit limit statement

## Task 7: Final Verification

**Files:**

- Verify all files changed in this plan

- [ ] **Step 1: Run all current tests**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_query_ask tests.test_health_check -v
```

Expected:

- all tests pass

- [ ] **Step 2: Run the health checker**

Run:

```bash
python3 tools/health_check.py .
```

Expected:

- `Vault health check passed`

- [ ] **Step 3: Check git status**

Run:

```bash
git status --short
```

Expected:

- changed files match the Query / Ask implementation scope
