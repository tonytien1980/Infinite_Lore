# Automation And Watcher Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first practical automation layer so the user can press `Scan now` in Workbench Inbox and process local intake plus configured RSS / article-list sources through deduped `import + compile`.

**Architecture:** Add a lightweight source-discovery and scan orchestration layer that sits on top of the existing importer/compiler instead of replacing them. Reuse the useful parts of Graphify's cache design for incremental behavior, keep source configuration outside the vault, and expose the whole flow through Inbox rather than adding a new top-level page.

**Tech Stack:** Python 3.9 standard library, FastAPI, unittest, existing Workbench frontend, existing importer/compiler modules, selective Graphify-inspired cache patterns

---

## File Structure

### New files

- `tools/automation_cache.py`
  - Purpose: Graphify-inspired lightweight cache helpers for source-discovery state, content-hash state, and atomic JSON writes.
- `tools/source_connectors.py`
  - Purpose: connector implementations for RSS feeds and single-page article-list discovery plus canonical URL normalization and dedup helpers.
- `tools/automation_scan.py`
  - Purpose: orchestrate `scan -> deduplicate -> import -> compile`, retry failed items, and return structured scan summaries.
- `workbench/source_store.py`
  - Purpose: persist configured sources and scan runtime state outside the vault, alongside the existing local workbench config.
- `tests/test_automation_scan.py`
  - Purpose: verify source discovery, deduplication, failed-item retry, and structured scan results.

### Modified files

- `workbench/server.py`
  - Add source-management and scan endpoints.
- `workbench/services.py`
  - Surface sources, last scan summary, failed counts, and scan execution to the UI layer.
- `workbench/static/index.html`
  - Extend Inbox with source management and scan results.
- `workbench/static/app.js`
  - Add source CRUD, `Scan now`, and Inbox scan-summary rendering.
- `workbench/static/app.css`
  - Style the new Inbox source-management and scan-summary sections.
- `tests/test_workbench_api.py`
  - Cover new API endpoints and scan behavior through the Workbench layer.
- `00_System/Workflow Guide.md`
  - Add the practical automation workflow after implementation.
- `docs/2026-04-08-execution-roadmap.md`
  - Mark Phase 7 as delivered after implementation.

### Reuse guidance from Graphify

- Reuse directly or adapt heavily from `graphify/cache.py`:
  - file hashing
  - atomic JSON write pattern
  - skip-unchanged behavior
- Reuse conceptually from `graphify/watch.py`:
  - split-by-cost logic
  - cheap discovery before expensive semantic work
- Do not transplant:
  - graph exports
  - graph UI
  - graph-first workflow

---

### Task 1: Add Local Source Store And Failing Tests

**Files:**
- Create: `workbench/source_store.py`
- Modify: `workbench/server.py`
- Modify: `workbench/services.py`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Write the failing API tests for source management**

Add these tests to `tests/test_workbench_api.py`:

```python
    def test_sources_round_trip_persists_rss_and_list_page_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            save_response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        },
                        {
                            "id": "list-sej",
                            "name": "Search Engine Journal",
                            "source_type": "article-list-page",
                            "url": "https://www.searchenginejournal.com/category/seo/",
                            "enabled": True,
                        },
                    ]
                },
            )
            load_response = client.get("/api/inbox/sources")

            self.assertEqual(save_response.status_code, 200)
            self.assertEqual(load_response.status_code, 200)
            payload = load_response.json()
            self.assertEqual(len(payload["sources"]), 2)
            self.assertEqual(payload["sources"][0]["source_type"], "rss-feed")
            self.assertEqual(payload["sources"][1]["source_type"], "article-list-page")

    def test_inbox_summary_returns_source_and_scan_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/inbox/summary")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("sources", payload)
            self.assertIn("last_scan", payload)
            self.assertIn("failed_count", payload)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_workbench_api.WorkbenchApiTests.test_sources_round_trip_persists_rss_and_list_page_sources tests.test_workbench_api.WorkbenchApiTests.test_inbox_summary_returns_source_and_scan_state -v
```

Expected:

- FAIL because `/api/inbox/sources` and `/api/inbox/summary` do not exist yet

- [ ] **Step 3: Create the local source store**

Create `workbench/source_store.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SOURCE_STATE: Dict[str, Any] = {
    "sources": [],
    "last_scan": None,
    "failed_items": [],
}


def load_source_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_SOURCE_STATE))

    payload = json.loads(path.read_text(encoding="utf-8"))
    state = json.loads(json.dumps(DEFAULT_SOURCE_STATE))
    state.update(payload)
    return state


def save_source_state(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return payload


def replace_sources(path: Path, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = load_source_state(path)
    state["sources"] = sources
    return save_source_state(path, state)


def summarize_source_state(path: Path) -> Dict[str, Any]:
    state = load_source_state(path)
    return {
        "sources": state.get("sources", []),
        "last_scan": state.get("last_scan"),
        "failed_count": len(state.get("failed_items", [])),
        "failed_items": state.get("failed_items", []),
    }
```

- [ ] **Step 4: Wire the new source endpoints**

Update `workbench/server.py` imports and routes:

```python
from workbench.source_store import load_source_state, replace_sources, summarize_source_state
```

Add inside `create_app(...)`:

```python
    source_state_path = config_path.with_name("automation-state.json")

    @app.get("/api/inbox/sources")
    def inbox_sources() -> dict:
        return {"sources": load_source_state(source_state_path).get("sources", [])}

    @app.post("/api/inbox/sources")
    def inbox_save_sources(payload: dict) -> dict:
        state = replace_sources(source_state_path, payload.get("sources", []))
        return {"sources": state.get("sources", [])}

    @app.get("/api/inbox/summary")
    def inbox_summary() -> dict:
        return summarize_source_state(source_state_path)
```

Update `workbench/services.py` with:

```python
from workbench.source_store import summarize_source_state


def get_inbox_summary(source_state_path: Path) -> Dict[str, object]:
    return summarize_source_state(source_state_path)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_workbench_api.WorkbenchApiTests.test_sources_round_trip_persists_rss_and_list_page_sources tests.test_workbench_api.WorkbenchApiTests.test_inbox_summary_returns_source_and_scan_state -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add workbench/source_store.py workbench/server.py workbench/services.py tests/test_workbench_api.py
git commit -m "feat: add inbox source state endpoints"
```

---

### Task 2: Build Connector Discovery And Dedup Helpers

**Files:**
- Create: `tools/automation_cache.py`
- Create: `tools/source_connectors.py`
- Create: `tests/test_automation_scan.py`

- [ ] **Step 1: Write failing connector and dedup tests**

Create `tests/test_automation_scan.py` with:

```python
import tempfile
import unittest
from pathlib import Path

from tools.source_connectors import discover_rss_items, discover_article_list_items, choose_canonical_url, dedup_candidates


RSS_XML = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Alpha</title><link>https://example.com/a</link></item>
<item><title>Beta</title><link>https://example.com/b</link></item>
</channel></rss>
"""

LIST_HTML = """
<html><body>
  <a href="https://example.com/a">Alpha</a>
  <a href="https://example.com/c">Gamma</a>
</body></html>
"""


class AutomationScanTests(unittest.TestCase):
    def test_discovers_rss_items(self) -> None:
        items = discover_rss_items(RSS_XML, "https://example.com/feed")
        self.assertEqual([item["url"] for item in items], ["https://example.com/a", "https://example.com/b"])

    def test_discovers_article_links_from_list_page(self) -> None:
        items = discover_article_list_items(LIST_HTML, "https://example.com/blog")
        self.assertEqual([item["url"] for item in items], ["https://example.com/a", "https://example.com/c"])

    def test_dedup_prefers_canonical_url_then_hash(self) -> None:
        unique = dedup_candidates(
            [
                {"canonical_url": "https://example.com/a", "content_hash": "h1"},
                {"canonical_url": "https://example.com/a", "content_hash": "h2"},
                {"canonical_url": "", "content_hash": "h3"},
                {"canonical_url": "", "content_hash": "h3"},
            ]
        )
        self.assertEqual(len(unique), 2)
```

- [ ] **Step 2: Run the connector tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_automation_scan -v
```

Expected:

- FAIL because `tools/source_connectors.py` does not exist yet

- [ ] **Step 3: Add Graphify-inspired cache helpers**

Create `tools/automation_cache.py` with:

```python
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def content_hash_bytes(payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(payload)
    return h.hexdigest()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Implement source connectors and dedup helpers**

Create `tools/source_connectors.py` with:

```python
from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Dict, List

from tools.automation_cache import content_hash_bytes


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.links.append(value)


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    clean = parsed._replace(fragment="", query="")
    return urllib.parse.urlunparse(clean)


def choose_canonical_url(url: str) -> str:
    return normalize_url(url)


def discover_rss_items(feed_bytes: bytes, source_url: str) -> List[Dict[str, str]]:
    root = ET.fromstring(feed_bytes)
    items: List[Dict[str, str]] = []
    for item in root.findall(".//item"):
        link = item.findtext("link", default="").strip()
        title = item.findtext("title", default="").strip()
        if link:
            items.append({"title": title or link, "url": normalize_url(link), "source_url": source_url})
    return items


def discover_article_list_items(html: str, source_url: str) -> List[Dict[str, str]]:
    parser = LinkCollector()
    parser.feed(html)
    base = normalize_url(source_url)
    seen = set()
    items: List[Dict[str, str]] = []
    for href in parser.links:
        absolute = urllib.parse.urljoin(base, href)
        normalized = normalize_url(absolute)
        if normalized in seen or normalized == base:
            continue
        seen.add(normalized)
        items.append({"title": normalized, "url": normalized, "source_url": source_url})
    return items


def dedup_candidates(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    kept: List[Dict[str, str]] = []
    seen_urls = set()
    seen_hashes = set()
    for item in items:
        canonical = item.get("canonical_url", "") or ""
        digest = item.get("content_hash", "") or ""
        if canonical and canonical in seen_urls:
            continue
        if digest and digest in seen_hashes:
            continue
        if canonical:
            seen_urls.add(canonical)
        if digest:
            seen_hashes.add(digest)
        kept.append(item)
    return kept
```

- [ ] **Step 5: Run the connector tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_automation_scan -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add tools/automation_cache.py tools/source_connectors.py tests/test_automation_scan.py
git commit -m "feat: add source connector discovery helpers"
```

---

### Task 3: Add Scan Orchestrator With Retry And Incremental State

**Files:**
- Create: `tools/automation_scan.py`
- Modify: `workbench/source_store.py`
- Modify: `tests/test_automation_scan.py`

- [ ] **Step 1: Add failing scan-orchestration tests**

Append to `tests/test_automation_scan.py`:

```python
from tools.automation_scan import run_scan

    def test_run_scan_imports_local_file_and_updates_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "20_Raw/inbox/note.txt").write_text("# Library Systems\n\nKnowledge access matters.\n", encoding="utf-8")

            result = run_scan(root, [], root / "automation-state.json")

            self.assertGreaterEqual(result["imported_count"], 1)
            self.assertGreaterEqual(result["compiled_count"], 1)
            self.assertEqual(result["failed_count"], 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_automation_scan.AutomationScanTests.test_run_scan_imports_local_file_and_updates_summary -v
```

Expected:

- FAIL because `tools/automation_scan.py` does not exist yet

- [ ] **Step 3: Extend source state to persist scan results**

Update `workbench/source_store.py` to support:

```python
def update_scan_state(path: Path, *, summary: Dict[str, Any], failed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = load_source_state(path)
    state["last_scan"] = summary
    state["failed_items"] = failed_items
    return save_source_state(path, state)
```

- [ ] **Step 4: Implement the scan orchestrator**

Create `tools/automation_scan.py` with:

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tools.import_bundle import import_source
from tools.wiki_compile import compile_bundle
from tools.source_connectors import dedup_candidates
from workbench.source_store import load_source_state, update_scan_state


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_local_candidates(vault_root: Path) -> List[Dict[str, Any]]:
    inbox = vault_root / "20_Raw/inbox"
    candidates: List[Dict[str, Any]] = []
    if not inbox.exists():
        return candidates
    for path in sorted(inbox.iterdir()):
        if path.is_file():
            candidates.append(
                {
                    "title": path.name,
                    "source": str(path),
                    "source_kind": "local-file",
                    "canonical_url": "",
                    "content_hash": "",
                    "primary_domain": "ai-application",
                }
            )
    return candidates


def run_scan(vault_root: Path, configured_sources: List[Dict[str, Any]], state_path: Path) -> Dict[str, Any]:
    state = load_source_state(state_path)
    failed_items = list(state.get("failed_items", []))
    candidates = discover_local_candidates(vault_root) + failed_items
    candidates = dedup_candidates(candidates)

    imported_count = 0
    compiled_count = 0
    new_failed: List[Dict[str, Any]] = []

    for candidate in candidates:
        try:
            bundle = import_source(vault_root, candidate["source"], candidate.get("primary_domain", "ai-application"))
            imported_count += 1
            compile_bundle(vault_root, bundle)
            compiled_count += 1
        except Exception:
            new_failed.append(candidate)

    summary = {
        "ran_at": now_iso(),
        "discovered_count": len(candidates),
        "deduplicated_count": len(candidates),
        "imported_count": imported_count,
        "compiled_count": compiled_count,
        "failed_count": len(new_failed),
    }
    update_scan_state(state_path, summary=summary, failed_items=new_failed)
    return summary
```

- [ ] **Step 5: Run the scan tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_automation_scan -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add tools/automation_scan.py workbench/source_store.py tests/test_automation_scan.py
git commit -m "feat: add practical scan orchestration"
```

---

### Task 4: Expose Scan Controls And Results In Workbench Inbox

**Files:**
- Modify: `workbench/server.py`
- Modify: `workbench/services.py`
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`
- Modify: `workbench/static/app.css`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add failing Workbench scan tests**

Append to `tests/test_workbench_api.py`:

```python
    def test_scan_now_endpoint_returns_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "20_Raw/inbox/note.txt").write_text("# Library Systems\n\nKnowledge access matters.\n", encoding="utf-8")
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post("/api/inbox/scan")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("imported_count", payload)
            self.assertIn("compiled_count", payload)
```

- [ ] **Step 2: Run the Workbench scan test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_workbench_api.WorkbenchApiTests.test_scan_now_endpoint_returns_summary -v
```

Expected:

- FAIL because `/api/inbox/scan` does not exist yet

- [ ] **Step 3: Add services and API endpoints**

Update `workbench/services.py` with:

```python
from tools.automation_scan import run_scan
from workbench.source_store import load_source_state, summarize_source_state


def run_inbox_scan(vault_root: Path, source_state_path: Path) -> Dict[str, object]:
    state = load_source_state(source_state_path)
    return run_scan(vault_root, state.get("sources", []), source_state_path)
```

Update `workbench/server.py` with:

```python
    @app.post("/api/inbox/scan")
    def inbox_scan() -> dict:
        return run_inbox_scan(vault_root, source_state_path)
```

- [ ] **Step 4: Extend Inbox UI**

Update `workbench/static/index.html` Inbox section so it includes:

```html
<section class="panel">
  <div class="panel-head split">
    <div>
      <p class="eyebrow">Configured Sources</p>
      <h3>Feeds and list pages</h3>
    </div>
  </div>
  <form id="sourceForm" class="stack-form">
    <label><span>Name</span><input type="text" id="sourceName" /></label>
    <label><span>Type</span>
      <select id="sourceType">
        <option value="rss-feed">RSS / Feed</option>
        <option value="article-list-page">Article list page</option>
      </select>
    </label>
    <label><span>URL</span><input type="url" id="sourceUrl" /></label>
    <button type="submit" class="secondary-button">Add source</button>
  </form>
  <div id="sourceList" class="list-stack empty-state">No sources configured yet.</div>
</section>

<section class="panel">
  <div class="panel-head split">
    <div>
      <p class="eyebrow">Scan Summary</p>
      <h3>Latest run</h3>
    </div>
    <button id="scanNowButton" class="primary-button" type="button">Scan now</button>
  </div>
  <div id="scanSummary" class="list-stack empty-state">No scan run yet.</div>
</section>
```

Update `workbench/static/app.js` with:

```javascript
async function loadInboxSummary() {
  const summary = await fetchJson("/api/inbox/summary");
  renderSources(summary.sources || []);
  renderScanSummary(summary.last_scan);
}

async function runInboxScan() {
  const result = await fetchJson("/api/inbox/scan", { method: "POST" });
  renderScanSummary(result);
  await loadAll();
  await loadInboxSummary();
}
```

Bind:

```javascript
document.getElementById("scanNowButton").addEventListener("click", runInboxScan);
```

Add matching visual treatment in `workbench/static/app.css` for:

```css
.scan-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}
```

- [ ] **Step 5: Run the API tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add workbench/server.py workbench/services.py workbench/static/index.html workbench/static/app.js workbench/static/app.css tests/test_workbench_api.py
git commit -m "feat: add inbox automation controls"
```

---

### Task 5: Finish Docs And Full Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-09-automation-watcher-spec.md` only if implementation changed behavior

- [ ] **Step 1: Update the workflow guide**

Append to `00_System/Workflow Guide.md`:

```md
## Automation And Scan Now

Use the Workbench Inbox for practical automation.

- Configure explicit sources inside Inbox.
- Press `Scan now` to process:
  - local intake
  - RSS / feed sources
  - configured article list pages
- The scan deduplicates candidates before running `import + compile`.
- Failed items remain visible and are retried by later scans.
```

- [ ] **Step 2: Update the execution roadmap**

Update `docs/2026-04-08-execution-roadmap.md` so:

- Phase 7 becomes delivered
- the next future direction remains Graphify-inspired relation and multimodal expansion

- [ ] **Step 3: Run the full verification suite**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_wiki_compile tests.test_workbench_api tests.test_query_ask tests.test_reflection_feedback tests.test_automation_scan tests.test_health_check -v
python3 tools/health_check.py .
```

Expected:

- all tests PASS
- health check prints `Vault health check passed`

- [ ] **Step 4: Commit**

```bash
git add 00_System/Workflow Guide.md docs/2026-04-08-execution-roadmap.md docs/2026-04-09-automation-watcher-spec.md docs/2026-04-09-automation-watcher-implementation-plan.md
git commit -m "docs: finish automation watcher rollout notes"
```

- [ ] **Step 5: Final sync**

```bash
git push origin codex/foundation-bootstrap
```

Expected:

- branch is clean
- local and remote are aligned

---

## Self-Review

- Spec coverage check:
  - source connectors, `Scan now`, retry, dedup, local + configured sources, Inbox integration, cache behavior, and post-phase docs sync are all mapped to tasks above.
- Placeholder scan:
  - no `TODO`, `TBD`, or deferred implementation placeholders remain in the plan steps.
- Type consistency:
  - the plan consistently uses `source_state_path`, `run_scan`, `summarize_source_state`, `rss-feed`, and `article-list-page`.
