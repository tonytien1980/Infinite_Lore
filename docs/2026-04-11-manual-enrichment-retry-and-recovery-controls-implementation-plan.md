# Manual Enrichment Retry And Recovery Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add single-bundle retry and dismiss controls for `failed` / `deferred` raw enrichment entries without introducing a new queue-management page.

**Architecture:** Keep `00_System/raw-enrichment-state.json` as the operational queue source of truth. Add narrow backend action helpers plus small API endpoints, then render inline `重試` / `清除` actions only inside `收件匣`. `摘要` stays read-only. Retry re-queues a bundle to `pending`; dismiss removes the active queue entry while leaving the raw bundle and sidecar intact.

**Tech Stack:** Python 3.9, FastAPI, existing `tools/raw_enrichment.py`, Workbench services/API, existing `workbench/static/app.js`, `unittest`, existing browser QA flow

---

## File Structure

- Modify: `tools/raw_enrichment.py`
  - add narrow queue action helpers for retry and dismiss
- Modify: `workbench/server.py`
  - expose `POST /api/enrichment/retry` and `POST /api/enrichment/dismiss`
- Modify: `workbench/services.py`
  - no new payload shape should be required, but small helper reuse is allowed if it keeps endpoints narrow
- Modify: `workbench/static/app.js`
  - render inline `重試` / `清除` controls in `收件匣` only when status is `failed` or `deferred`
- Modify: `tests/test_raw_enrichment.py`
  - queue action unit tests
- Modify: `tests/test_workbench_api.py`
  - retry / dismiss API tests
- Modify after implementation: `00_System/Workflow Guide.md`
  - explain manual retry and dismiss controls
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark the phase delivered and move the next action forward
- Modify after implementation: `docs/2026-04-11-manual-enrichment-retry-and-recovery-controls-spec.md`
  - update status from review-ready to delivered

This structure keeps queue semantics in `tools/raw_enrichment.py`, transport in `server.py`, and UI action wiring in the existing inbox surface only.

## Task 1: Add Red Tests For Queue Retry And Dismiss Helpers

**Files:**
- Modify: `tests/test_raw_enrichment.py`

- [ ] **Step 1: Write failing queue-action tests**

Append tests like:

```python
    def test_retry_bundle_for_enrichment_requeues_failed_entry_as_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "retry-me"
            bundle.mkdir(parents=True)
            state_path = default_enrichment_state_path(root)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "pending_bundles": [
                            {
                                "bundle_path": "20_Raw/inbox/retry-me",
                                "status": "failed",
                                "provider": "openai",
                                "model": "gpt-5.4-mini",
                                "failure_reason": "OpenAI boom",
                                "queued_at": "2026-04-11T00:00:00Z",
                                "updated_at": "2026-04-11T00:00:00Z",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = retry_bundle_for_enrichment(root, "20_Raw/inbox/retry-me")

            self.assertEqual(result["bundle_path"], "20_Raw/inbox/retry-me")
            self.assertEqual(result["enrichment_status"], "pending")
```

and:

```python
    def test_dismiss_bundle_from_enrichment_queue_removes_active_entry_but_keeps_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "dismiss-me"
            bundle.mkdir(parents=True)
            state_path = default_enrichment_state_path(root)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "pending_bundles": [
                            {
                                "bundle_path": "20_Raw/inbox/dismiss-me",
                                "status": "deferred",
                                "provider": "ollama",
                                "model": "qwen3:14b",
                                "failure_reason": "unsupported provider",
                                "queued_at": "2026-04-11T00:00:00Z",
                                "updated_at": "2026-04-11T00:00:00Z",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = dismiss_bundle_from_enrichment_queue(root, "20_Raw/inbox/dismiss-me")

            self.assertEqual(result["bundle_path"], "20_Raw/inbox/dismiss-me")
            self.assertTrue(result["dismissed"])
            self.assertTrue(bundle.exists())
```

- [ ] **Step 2: Run the focused tests to confirm RED**

Run:

```bash
python3 -m unittest \
  tests.test_raw_enrichment.RawEnrichmentQueueTests.test_retry_bundle_for_enrichment_requeues_failed_entry_as_pending \
  tests.test_raw_enrichment.RawEnrichmentQueueTests.test_dismiss_bundle_from_enrichment_queue_removes_active_entry_but_keeps_bundle -v
```

Expected:

- FAIL because the queue action helpers do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_raw_enrichment.py
git commit -m "test: add enrichment retry and dismiss queue coverage"
```

## Task 2: Implement Queue Retry And Dismiss Helpers

**Files:**
- Modify: `tools/raw_enrichment.py`
- Modify: `tests/test_raw_enrichment.py`

- [ ] **Step 1: Add narrow queue action helpers**

Add to `tools/raw_enrichment.py`:

```python
def retry_bundle_for_enrichment(root: Path, bundle_path_text: str) -> Dict[str, Any]:
    bundle_path = (root / bundle_path_text).resolve()
    if not bundle_path.exists() or not bundle_path.is_dir():
        raise ValueError("bundle_path does not exist")
    bundle_path.relative_to(root.resolve())
    queue_bundle_for_enrichment(root, bundle_path)
    sidecar = _load_json_dict(default_enrichment_path(bundle_path))
    return {
        "bundle_path": bundle_path.relative_to(root).as_posix(),
        "enrichment_status": str(sidecar.get("status", "") or ""),
        "enrichment_updated_at": str(sidecar.get("updated_at", "") or ""),
    }


def dismiss_bundle_from_enrichment_queue(root: Path, bundle_path_text: str) -> Dict[str, Any]:
    bundle_path = (root / bundle_path_text).resolve()
    bundle_path.relative_to(root.resolve())
    state_path = default_enrichment_state_path(root)
    state_payload = _load_json_dict(state_path, preserve_corrupt=True)
    pending_bundles = state_payload.get("pending_bundles")
    if not isinstance(pending_bundles, list):
        pending_bundles = []

    filtered = [
        entry
        for entry in pending_bundles
        if not isinstance(entry, dict) or str(entry.get("bundle_path") or "") != bundle_path.relative_to(root).as_posix()
    ]
    if len(filtered) == len(pending_bundles):
        raise ValueError("no active queue entry for bundle_path")

    state_payload["pending_bundles"] = filtered
    state_payload["updated_at"] = now_iso()
    _write_json_atomic(state_path, state_payload)
    return {"bundle_path": bundle_path.relative_to(root).as_posix(), "dismissed": True}
```

- [ ] **Step 2: Run the queue-action tests again**

Run:

```bash
python3 -m unittest \
  tests.test_raw_enrichment.RawEnrichmentQueueTests.test_retry_bundle_for_enrichment_requeues_failed_entry_as_pending \
  tests.test_raw_enrichment.RawEnrichmentQueueTests.test_dismiss_bundle_from_enrichment_queue_removes_active_entry_but_keeps_bundle -v
```

Expected:

- PASS

- [ ] **Step 3: Run the full raw enrichment suite**

Run:

```bash
python3 -m unittest tests.test_raw_enrichment -v
```

Expected:

- PASS

- [ ] **Step 4: Commit**

```bash
git add tools/raw_enrichment.py tests/test_raw_enrichment.py
git commit -m "feat: add enrichment retry and dismiss helpers"
```

## Task 3: Add Red Tests For Retry And Dismiss API Endpoints

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Write failing API tests**

Append tests like:

```python
    def test_retry_endpoint_requeues_failed_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw/inbox/retry-me"
            bundle.mkdir(parents=True)
            (bundle / "enrichment.json").write_text(
                json.dumps({"status": "failed", "updated_at": "2026-04-11T00:00:00Z"}) + "\n",
                encoding="utf-8",
            )
            state_path = root / "00_System" / "raw-enrichment-state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"pending_bundles": [{"bundle_path": "20_Raw/inbox/retry-me", "status": "failed"}]}) + "\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post("/api/enrichment/retry", json={"bundle_path": "20_Raw/inbox/retry-me"})

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["bundle_path"], "20_Raw/inbox/retry-me")
            self.assertEqual(payload["enrichment_status"], "pending")
```

and:

```python
    def test_dismiss_endpoint_clears_active_queue_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw/inbox/dismiss-me"
            bundle.mkdir(parents=True)
            state_path = root / "00_System" / "raw-enrichment-state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"pending_bundles": [{"bundle_path": "20_Raw/inbox/dismiss-me", "status": "deferred"}]}) + "\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post("/api/enrichment/dismiss", json={"bundle_path": "20_Raw/inbox/dismiss-me"})

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["dismissed"])
```

- [ ] **Step 2: Run the focused API tests to confirm RED**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_retry_endpoint_requeues_failed_bundle \
  tests.test_workbench_api.WorkbenchApiTests.test_dismiss_endpoint_clears_active_queue_entry -v
```

Expected:

- FAIL because the endpoints do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_workbench_api.py
git commit -m "test: add enrichment retry and dismiss api coverage"
```

## Task 4: Implement Retry And Dismiss API Endpoints

**Files:**
- Modify: `workbench/server.py`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add the endpoints**

In `workbench/server.py`, add:

```python
from tools.raw_enrichment import dismiss_bundle_from_enrichment_queue, retry_bundle_for_enrichment
```

and:

```python
    @app.post("/api/enrichment/retry")
    def enrichment_retry(payload: dict) -> dict:
        try:
            return retry_bundle_for_enrichment(vault_root, payload["bundle_path"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/enrichment/dismiss")
    def enrichment_dismiss(payload: dict) -> dict:
        try:
            return dismiss_bundle_from_enrichment_queue(vault_root, payload["bundle_path"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 2: Run the focused API tests again**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_retry_endpoint_requeues_failed_bundle \
  tests.test_workbench_api.WorkbenchApiTests.test_dismiss_endpoint_clears_active_queue_entry -v
```

Expected:

- PASS

- [ ] **Step 3: Commit**

```bash
git add workbench/server.py tests/test_workbench_api.py
git commit -m "feat: add enrichment retry and dismiss endpoints"
```

## Task 5: Render Inline Controls In Inbox Only

**Files:**
- Modify: `workbench/static/app.js`

- [ ] **Step 1: Add retry and dismiss actions to bundle rows**

Update `workbench/static/app.js` so `renderBundles()` renders inline buttons only when:

- `bundle.enrichment_status === "failed"`
- or `bundle.enrichment_status === "deferred"`

Recommended small helpers:

```javascript
async function retryEnrichment(bundlePath) {
  await fetchJson("/api/enrichment/retry", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bundle_path: bundlePath }),
  });
  await loadAll();
}

async function dismissEnrichment(bundlePath) {
  await fetchJson("/api/enrichment/dismiss", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bundle_path: bundlePath }),
  });
  await loadAll();
}
```

Inside each bundle list item:

- add `重試` button for `failed` / `deferred`
- add `清除` button for `failed` / `deferred`

Do not add these buttons to `摘要`.

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
git commit -m "feat: add inbox enrichment retry controls"
```

## Task 6: Live Verification And Docs Sync

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-11-manual-enrichment-retry-and-recovery-controls-spec.md`

- [ ] **Step 1: Update the active docs**

Update `00_System/Workflow Guide.md` to reflect:

- `收件匣` now exposes inline `重試` and `清除` controls for `failed` / `deferred`
- `摘要` remains read-only
- retry returns a bundle to `pending`
- dismiss clears the active queue entry without deleting the raw bundle

Update `docs/2026-04-11-manual-enrichment-retry-and-recovery-controls-spec.md` to:

```md
**Status:** Delivered and verified locally
```

Update `docs/2026-04-08-execution-roadmap.md` so the next action moves to the next post-retry planning target.

- [ ] **Step 2: Run full verification**

Run:

```bash
python3 -m unittest tests.test_raw_enrichment tests.test_workbench_api tests.test_background_enrichment -v
python3 tools/health_check.py .
/Users/oldtien_base/.nvm/versions/node/v24.14.1/bin/node --check workbench/static/app.js
git diff --check
```

Then run live local verification:

1. start Workbench
2. prepare a bundle in `failed` or `deferred`
3. open `收件匣`
4. confirm `重試` and `清除` are visible there
5. confirm `摘要` remains read-only
6. click `重試` and confirm the bundle returns to `pending`
7. click `清除` on a `failed` or `deferred` bundle and confirm the active queue entry disappears while the raw bundle remains on disk

- [ ] **Step 3: Commit docs sync**

```bash
git add \
  00_System/Workflow\ Guide.md \
  docs/2026-04-08-execution-roadmap.md \
  docs/2026-04-11-manual-enrichment-retry-and-recovery-controls-spec.md
git commit -m "docs: sync enrichment retry controls delivery"
```
