# Workbench UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local Workbench UI for Infinite Lore so non-Obsidian workflows can be used through a browser-based interface instead of the terminal.

**Architecture:** The implementation uses a Python local backend plus a local web frontend that shares the same vault as Obsidian. The backend exposes import, compile visibility, health, and local settings endpoints; the frontend provides the `Home`, `Inbox`, `Knowledge`, `Ask`, `System`, and `Settings` pages as a single local web application.

**Tech Stack:** Python 3.9, FastAPI, Uvicorn, `unittest`, `httpx`, `python-multipart`, vanilla HTML/CSS/JavaScript, existing importer/compiler/health tools

---

## File Structure

### Files to create

- `docs/2026-04-08-workbench-ui-implementation-plan.md`
- `workbench/__init__.py`
- `workbench/config_store.py`
- `workbench/services.py`
- `workbench/server.py`
- `workbench/static/index.html`
- `workbench/static/app.css`
- `workbench/static/app.js`
- `tools/run_workbench.py`
- `tests/test_workbench_api.py`

### Files to modify

- `requirements.txt`
- `00_System/Workflow Guide.md`

## Task 1: Add Workbench Runtime Dependencies And Launch Guidance

**Files:**

- Modify: `requirements.txt`
- Modify: `00_System/Workflow Guide.md`
- Create: `tools/run_workbench.py`

- [ ] **Step 1: Add the workbench runtime dependencies**

Replace `requirements.txt` with:

```txt
pypdf>=6.9,<7
fastapi>=0.116,<1
uvicorn>=0.35,<1
httpx>=0.28,<1
python-multipart>=0.0.20,<1
```

- [ ] **Step 2: Add a workbench launch section to the workflow guide**

Append this section to `00_System/Workflow Guide.md`:

```md
## Workbench UI

Run the local Workbench UI with:

```bash
python3 tools/run_workbench.py
```

Then open the local URL shown in the terminal.
```

- [ ] **Step 3: Add a simple runner script**

Create `tools/run_workbench.py` with:

```python
from workbench.server import run


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Verify the dependency and launch docs are present**

Run:

```bash
rg --files requirements.txt 00_System tools/run_workbench.py
```

Expected:

- output includes `requirements.txt`
- output includes the updated workflow guide
- output includes `tools/run_workbench.py`

## Task 2: Write Failing Backend API Tests

**Files:**

- Create: `tests/test_workbench_api.py`

- [ ] **Step 1: Write tests for dashboard, import, knowledge listing, and settings persistence**

Create `tests/test_workbench_api.py` with:

```python
import io
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from workbench.server import create_app


class WorkbenchApiTests(unittest.TestCase):
    def make_client(self, root: Path, config_path: Path) -> TestClient:
        app = create_app(vault_root=root, config_path=config_path)
        return TestClient(app)

    def test_dashboard_returns_core_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            (root / "20_Raw/inbox/example").mkdir()
            (root / "20_Raw/inbox/example/metadata.md").write_text(
                "---\nprimary_domain: ai-application\nsource_refs: []\nconversion_status: converted\n---\n",
                encoding="utf-8",
            )
            (root / "20_Raw/inbox/example/content.md").write_text("hello\n", encoding="utf-8")
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/dashboard")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("bundle_count", payload)
            self.assertIn("knowledge_count", payload)

    def test_import_file_endpoint_creates_bundle_and_wiki_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/import-file",
                files={"file": ("sample.txt", b"# Library Systems\n\nA library system organizes knowledge.\n", "text/plain")},
                data={"primary_domain": "ai-application"},
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("bundle_path", payload)
            self.assertTrue((root / payload["bundle_path"]).exists())
            self.assertTrue((root / "30_Wiki/ai-application/library-systems--synthesis.md").exists())

    def test_knowledge_endpoint_lists_synthesis_and_small_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "30_Wiki/ai-application/a-note--synthesis.md").write_text(
                "---\nnote_type: synthesis\nprimary_domain: ai-application\nsource_refs: []\n---\n",
                encoding="utf-8",
            )
            (root / "30_Wiki/ai-application/a-note--concept--knowledge.md").write_text(
                "---\nnote_type: concept\nprimary_domain: ai-application\nsource_refs: []\n---\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/knowledge")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload["synthesis"]), 1)
            self.assertEqual(len(payload["small_notes"]), 1)

    def test_settings_round_trip_persists_model_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            client = self.make_client(root, config_path)

            save_response = client.post(
                "/api/settings",
                json={
                    "providers": [
                        {
                            "id": "openai-main",
                            "provider": "openai",
                            "api_key": "sk-test",
                            "models": [
                                {"id": "gpt-best", "role": "best_deep"},
                                {"id": "gpt-balanced", "role": "balanced"},
                            ],
                        }
                    ],
                    "routes": {
                        "scan": "no_model",
                        "compile": "balanced",
                        "ask": "best_deep",
                    },
                },
            )
            load_response = client.get("/api/settings")

            self.assertEqual(save_response.status_code, 200)
            self.assertEqual(load_response.status_code, 200)
            payload = load_response.json()
            self.assertEqual(payload["routes"]["ask"], "best_deep")
            self.assertEqual(payload["providers"][0]["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- failure because the `workbench` backend modules do not exist yet

## Task 3: Implement The Python Backend

**Files:**

- Create: `workbench/__init__.py`
- Create: `workbench/config_store.py`
- Create: `workbench/services.py`
- Create: `workbench/server.py`

- [ ] **Step 1: Install the dependencies for local development**

Run:

```bash
python3 -m pip install -r requirements.txt
```

Expected:

- FastAPI and related packages install successfully

- [ ] **Step 2: Create `workbench/config_store.py`**

Create `workbench/config_store.py` with functions that:

- load local config JSON from a file path outside the vault by default
- save provider and routing configuration
- return a default empty config when no file exists

The module should expose:

- `load_config(path: Path) -> dict`
- `save_config(path: Path, config: dict) -> dict`

- [ ] **Step 3: Create `workbench/services.py`**

Create `workbench/services.py` with service helpers that:

- scan raw bundles
- summarize dashboard counts
- list compiled knowledge notes
- call `import_source(...)`
- call `compile_bundle(...)`
- call `check_vault(...)`

The module should expose at least:

- `get_dashboard(vault_root: Path) -> dict`
- `list_bundles(vault_root: Path) -> list`
- `list_knowledge(vault_root: Path) -> dict`
- `import_file(vault_root: Path, file_name: str, file_bytes: bytes, primary_domain: str) -> dict`
- `import_url(vault_root: Path, url: str, primary_domain: str) -> dict`
- `get_health(vault_root: Path) -> dict`

- [ ] **Step 4: Create `workbench/server.py`**

Create `workbench/server.py` with:

- `create_app(vault_root: Path | None = None, config_path: Path | None = None) -> FastAPI`
- static file serving for `workbench/static`
- JSON API routes:
  - `GET /api/dashboard`
  - `GET /api/bundles`
  - `GET /api/knowledge`
  - `GET /api/system/health`
  - `GET /api/settings`
  - `POST /api/settings`
  - `POST /api/inbox/import-file`
  - `POST /api/inbox/import-url`
- `run()` helper using Uvicorn on `127.0.0.1:8765`

- [ ] **Step 5: Run the backend tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- all 4 tests pass

## Task 4: Build The Frontend Workbench UI

**Files:**

- Create: `workbench/static/index.html`
- Create: `workbench/static/app.css`
- Create: `workbench/static/app.js`

- [ ] **Step 1: Create the HTML shell**

Create `workbench/static/index.html` with:

- a sidebar for:
  - Home
  - Inbox
  - Knowledge
  - Ask
  - System
  - Settings
- a top title area for `Infinite Lore Workbench`
- a main content area that can switch views

- [ ] **Step 2: Create the CSS system**

Create `workbench/static/app.css` with:

- a calm, professional visual direction
- clear navigation hierarchy
- responsive desktop/mobile layout
- purposeful typography and spacing
- distinct panel styles for:
  - Ask area
  - activity cards
  - bundle tables
  - settings forms
  - health state indicators

- [ ] **Step 3: Create the frontend logic**

Create `workbench/static/app.js` with logic for:

- initial dashboard load
- page navigation
- inbox bundle list rendering
- file import submission
- URL import submission
- knowledge list rendering
- system health rendering
- settings load/save
- Ask page shell with:
  - prompt input
  - empty state message that grounded Ask integration is the next backend phase
  - reserved grounding and trace panels

- [ ] **Step 4: Verify the frontend files exist**

Run:

```bash
rg --files workbench/static
```

Expected:

- output includes `index.html`
- output includes `app.css`
- output includes `app.js`

## Task 5: Manual Browser Verification

**Files:**

- Verify all created frontend and backend files

- [ ] **Step 1: Start the local workbench server**

Run:

```bash
python3 tools/run_workbench.py
```

Expected:

- server starts on `http://127.0.0.1:8765`

- [ ] **Step 2: Verify the UI in a browser**

Check:

- `Home` loads with Ask-first hybrid layout
- `Inbox` shows intake controls and bundle list
- `Knowledge` shows synthesis and small-note sections
- `System` shows health status
- `Settings` allows saving provider and route settings

- [ ] **Step 3: Verify file import through the UI**

Use the UI to import a small text file and confirm:

- a new raw bundle appears
- compile output appears in Knowledge
- the dashboard updates

## Task 6: Final Verification

**Files:**

- Verify all files changed in this plan

- [ ] **Step 1: Run all current tests**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_health_check -v
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

- changed files match the Workbench implementation scope
