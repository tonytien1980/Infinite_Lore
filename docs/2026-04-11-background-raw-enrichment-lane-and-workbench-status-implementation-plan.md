# Background Raw Enrichment Lane And Workbench Status Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote raw enrichment from the current bounded manual runner into a lightweight server-owned background lane and surface enrichment state clearly in the existing Workbench UI.

**Architecture:** Keep the current queue and bounded runner as the core execution primitive, then add a single local background worker owned by the Workbench server lifecycle. Extend bundle and dashboard payloads with enrichment status fields, and render those statuses inside the existing `摘要` and `收件匣` surfaces without adding a new page or model-control clutter.

**Tech Stack:** Python 3.9, FastAPI lifecycle hooks, `unittest`, existing `tools/raw_enrichment.py`, Workbench services/API, existing `workbench/static/app.js`, existing local browser QA flow

---

## File Structure

- Create: `workbench/background_enrichment.py`
  - owns the lightweight poller, bounded drain loop, and lifecycle-safe start/stop helpers
- Modify: `workbench/server.py`
  - attach the background worker to FastAPI startup/shutdown
- Modify: `tools/raw_enrichment.py`
  - expose any tiny helper(s) needed by the background worker without changing the honest queue state machine
- Modify: `workbench/services.py`
  - expose enrichment status fields on bundle and dashboard payloads
- Modify: `workbench/static/app.js`
  - render enrichment status text inside existing recent-import and bundle-list cards
- Create: `tests/test_background_enrichment.py`
  - server-owned poller red/green coverage
- Modify: `tests/test_workbench_api.py`
  - API payload coverage for bundle and dashboard enrichment fields
- Modify after implementation: `00_System/Workflow Guide.md`
  - describe the background lane and visible enrichment states
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark the phase delivered and move the next action forward
- Modify after implementation: `docs/2026-04-11-background-raw-enrichment-lane-and-workbench-status-spec.md`
  - update status from review-ready to delivered

This structure keeps execution, lifecycle, API visibility, and UI rendering separated into focused files.

## Task 1: Add Red Tests For Background Worker Lifecycle

**Files:**
- Create: `tests/test_background_enrichment.py`

- [ ] **Step 1: Write failing tests for bounded poller behavior**

Create `tests/test_background_enrichment.py` with tests like:

```python
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from workbench.background_enrichment import BackgroundEnrichmentWorker


class BackgroundEnrichmentWorkerTests(unittest.TestCase):
    def test_run_once_processes_single_bounded_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            fake_process = mock.Mock(return_value={"processed": 1, "completed": 1, "deferred": 0, "failed": 0, "results": []})

            worker = BackgroundEnrichmentWorker(
                vault_root=root,
                config_path=config_path,
                poll_interval_seconds=15,
                batch_size=1,
                process_pending=fake_process,
            )

            result = worker.run_once()

            self.assertEqual(result["processed"], 1)
            fake_process.assert_called_once_with(root, config_path, limit=1)

    def test_worker_start_and_stop_toggle_running_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            worker = BackgroundEnrichmentWorker(
                vault_root=root,
                config_path=config_path,
                poll_interval_seconds=15,
                batch_size=1,
                process_pending=mock.Mock(return_value={"processed": 0, "completed": 0, "deferred": 0, "failed": 0, "results": []}),
            )

            worker.start()
            self.assertTrue(worker.is_running)
            worker.stop()
            self.assertFalse(worker.is_running)
```

- [ ] **Step 2: Run the new worker tests to confirm RED**

Run:

```bash
python3 -m unittest tests.test_background_enrichment -v
```

Expected:

- FAIL because `workbench.background_enrichment` does not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_background_enrichment.py
git commit -m "test: add background raw enrichment worker coverage"
```

## Task 2: Implement The Server-Owned Background Worker

**Files:**
- Create: `workbench/background_enrichment.py`
- Modify: `workbench/server.py`
- Modify: `tests/test_background_enrichment.py`

- [ ] **Step 1: Implement a bounded worker module**

Create `workbench/background_enrichment.py` with a small lifecycle-safe worker:

```python
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from tools.raw_enrichment import process_pending_enrichment


class BackgroundEnrichmentWorker:
    def __init__(
        self,
        *,
        vault_root: Path,
        config_path: Path,
        poll_interval_seconds: int = 15,
        batch_size: int = 1,
        process_pending: Callable[..., Dict[str, Any]] = process_pending_enrichment,
    ) -> None:
        self.vault_root = vault_root
        self.config_path = config_path
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self.process_pending = process_pending
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_once(self) -> Dict[str, Any]:
        return self.process_pending(self.vault_root, self.config_path, limit=self.batch_size)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                # Fail closed and retry on the next cycle; do not crash the server thread.
                pass
            self._stop_event.wait(self.poll_interval_seconds)

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="background-raw-enrichment", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2)
```

- [ ] **Step 2: Attach the worker to FastAPI lifecycle**

Update `workbench/server.py` so `create_app(...)` creates one worker and stores it in `app.state`:

```python
from workbench.background_enrichment import BackgroundEnrichmentWorker
```

and inside `create_app(...)`:

```python
    worker = BackgroundEnrichmentWorker(vault_root=vault_root, config_path=config_path)
    app.state.background_enrichment_worker = worker

    @app.on_event("startup")
    def startup_background_enrichment() -> None:
        worker.start()

    @app.on_event("shutdown")
    def shutdown_background_enrichment() -> None:
        worker.stop()
```

- [ ] **Step 3: Run the worker tests again**

Run:

```bash
python3 -m unittest tests.test_background_enrichment -v
```

Expected:

- PASS for the new worker lifecycle tests

- [ ] **Step 4: Commit**

```bash
git add workbench/background_enrichment.py workbench/server.py tests/test_background_enrichment.py
git commit -m "feat: add background raw enrichment worker"
```

## Task 3: Add Red Tests For Enrichment Status API Visibility

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add failing API tests for bundle and dashboard enrichment fields**

Append tests like:

```python
    def test_bundles_endpoint_exposes_enrichment_status_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw/inbox/example"
            bundle.mkdir(parents=True)
            (bundle / "metadata.md").write_text(
                "---\n"
                "title: Example\n"
                "primary_domain: ai-application\n"
                "conversion_status: converted\n"
                "---\n",
                encoding="utf-8",
            )
            (bundle / "enrichment.json").write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "provider": "openai",
                        "model": "gpt-5.4-mini",
                        "failure_reason": "OpenAI boom",
                        "updated_at": "2026-04-11T00:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/bundles")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload[0]["enrichment_status"], "failed")
            self.assertEqual(payload[0]["enrichment_provider"], "openai")
            self.assertEqual(payload[0]["enrichment_model"], "gpt-5.4-mini")
            self.assertEqual(payload[0]["enrichment_failure_reason"], "OpenAI boom")

    def test_dashboard_recent_imports_expose_enrichment_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw/inbox/example"
            bundle.mkdir(parents=True)
            (bundle / "metadata.md").write_text(
                "---\n"
                "title: Example\n"
                "primary_domain: ai-application\n"
                "conversion_status: converted\n"
                "---\n",
                encoding="utf-8",
            )
            (bundle / "enrichment.json").write_text(
                json.dumps({"status": "pending", "updated_at": "2026-04-11T00:00:00Z"}) + "\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/dashboard")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["recent_imports"][0]["enrichment_status"], "pending")
            self.assertEqual(payload["recent_imports"][0]["enrichment_updated_at"], "2026-04-11T00:00:00Z")
```

- [ ] **Step 2: Run the targeted API tests to confirm RED**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_exposes_enrichment_status_fields \
  tests.test_workbench_api.WorkbenchApiTests.test_dashboard_recent_imports_expose_enrichment_status -v
```

Expected:

- FAIL because the current service payloads do not yet expose these enrichment fields

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_workbench_api.py
git commit -m "test: cover enrichment status api visibility"
```

## Task 4: Implement Bundle And Dashboard Enrichment Visibility

**Files:**
- Modify: `workbench/services.py`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Read enrichment sidecars through a small helper**

Add to `workbench/services.py`:

```python
def _read_enrichment(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
```

Use it in `get_dashboard(...)` and `list_bundles(...)` by reading `bundle / "enrichment.json"` and adding:

```python
"enrichment_status": enrichment.get("status", ""),
"enrichment_provider": enrichment.get("provider", ""),
"enrichment_model": enrichment.get("model", ""),
"enrichment_failure_reason": enrichment.get("failure_reason", ""),
"enrichment_updated_at": enrichment.get("updated_at", ""),
```

Dashboard recent imports should include the narrower subset:

```python
"enrichment_status": enrichment.get("status", ""),
"enrichment_updated_at": enrichment.get("updated_at", ""),
```

- [ ] **Step 2: Run the targeted API tests again**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_exposes_enrichment_status_fields \
  tests.test_workbench_api.WorkbenchApiTests.test_dashboard_recent_imports_expose_enrichment_status -v
```

Expected:

- PASS

- [ ] **Step 3: Commit**

```bash
git add workbench/services.py tests/test_workbench_api.py
git commit -m "feat: expose enrichment status in workbench api"
```

## Task 5: Render Enrichment Status In Existing Workbench Surfaces

**Files:**
- Modify: `workbench/static/app.js`

- [ ] **Step 1: Render enrichment status inside recent imports and bundle list**

Update `workbench/static/app.js` so:

- recent import cards in `renderDashboard()` include enrichment state text
- bundle list items in `renderBundles()` include enrichment state text

Use a tiny formatter helper:

```javascript
function formatEnrichmentStatus(item) {
  const status = item?.enrichment_status || "";
  if (!status) return "整理狀態：尚未排入 enrichment";
  if (status === "pending") return "整理狀態：等待背景整理";
  if (status === "completed") return "整理狀態：已完成 enrichment";
  if (status === "failed") return `整理狀態：失敗${item?.enrichment_failure_reason ? ` • ${item.enrichment_failure_reason}` : ""}`;
  if (status === "deferred") return `整理狀態：延後${item?.enrichment_failure_reason ? ` • ${item.enrichment_failure_reason}` : ""}`;
  return `整理狀態：${status}`;
}
```

Then append that line to the existing `detail` strings for recent imports and bundle list rows.

- [ ] **Step 2: Run frontend syntax verification**

Run:

```bash
/Users/oldtien_base/.nvm/versions/node/v24.14.1/bin/node --check workbench/static/app.js
```

Expected:

- PASS

- [ ] **Step 3: Commit**

```bash
git add workbench/static/app.js
git commit -m "feat: show enrichment status in workbench"
```

## Task 6: Live Verification And Docs Sync

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-11-background-raw-enrichment-lane-and-workbench-status-spec.md`

- [ ] **Step 1: Update the active docs**

Update `00_System/Workflow Guide.md` to reflect:

- raw enrichment is now drained automatically while the Workbench server is running
- status is visible in recent imports and bundle list
- the bounded manual runner still exists as a maintenance/debug surface

Update `docs/2026-04-11-background-raw-enrichment-lane-and-workbench-status-spec.md` to:

```md
**Status:** Delivered and verified locally
```

and clarify that the delivered version is:

- a single-worker server-owned background poller
- bounded batch size `1`
- status visible in existing Workbench surfaces

Update `docs/2026-04-08-execution-roadmap.md` so the next action moves to the next planning target after this phase.

- [ ] **Step 2: Run full verification**

Run:

```bash
python3 -m unittest tests.test_background_enrichment tests.test_raw_enrichment tests.test_query_ask tests.test_workbench_api tests.test_app_shell -v
python3 tools/health_check.py .
/Users/oldtien_base/.nvm/versions/node/v24.14.1/bin/node --check workbench/static/app.js
git diff --check
```

Then run live local verification:

```bash
python3 tools/run_workbench.py
```

Verify manually in the browser:

- import or seed a bundle with `enrichment_status: pending`
- confirm the status becomes visible in `摘要` and `收件匣`
- wait for one poll cycle
- confirm a runnable OpenAI route changes the visible status to `completed`, or a non-runnable route remains `deferred` honestly

- [ ] **Step 3: Commit docs sync**

```bash
git add \
  00_System/Workflow\ Guide.md \
  docs/2026-04-08-execution-roadmap.md \
  docs/2026-04-11-background-raw-enrichment-lane-and-workbench-status-spec.md
git commit -m "docs: sync background enrichment lane delivery"
```
