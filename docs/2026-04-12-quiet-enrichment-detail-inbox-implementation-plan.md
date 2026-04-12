# Quiet Enrichment Detail In Inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a low-noise enrichment preview plus inline expand/collapse detail inside `收件匣` without changing `摘要` into a detail surface or exposing model-maintenance clutter by default.

**Architecture:** Extend the existing `/api/bundles` payload with quiet-detail enrichment fields already stored in bundle-local `enrichment.json`, then let the Workbench bundle list render one compact preview line and an optional inline detail panel per bundle row. Keep the summary page unchanged, keep retry / dismiss controls working where they already appear, and use progressive disclosure instead of a new detail page.

**Tech Stack:** Python 3.9, FastAPI services/API, existing `tools/raw_enrichment.py` sidecar contract, `unittest`, existing `workbench/static/app.js`, existing `workbench/static/app.css`, existing local browser QA flow

---

## File Structure

- Modify: `workbench/services.py`
  - extend bundle payloads with quiet-detail enrichment fields sourced from `enrichment.json`
- Modify: `workbench/static/app.js`
  - render one-line quiet previews plus inline `查看詳情` / `收起詳情` behavior inside `收件匣`
- Modify: `workbench/static/app.css`
  - add calm visual treatment for the preview row and expanded detail block
- Modify: `tests/test_workbench_api.py`
  - add bundle-payload coverage for quiet-detail fields and script-contract coverage for the inbox-only progressive disclosure behavior
- Modify after implementation: `00_System/Workflow Guide.md`
  - explain that quiet per-bundle enrichment detail now lives only in `收件匣`
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark the quiet-detail phase delivered and move the next action forward
- Modify after implementation: `docs/2026-04-12-quiet-enrichment-detail-inbox-spec.md`
  - update status from review-ready to delivered
- Modify after implementation: `00_System/Home.md`
  - link the implementation plan beside the spec

This structure keeps enrichment data shaping in the service layer, interaction logic in `app.js`, visual restraint in `app.css`, and docs synced after the UI behavior is verified.

## Task 1: Add Red Tests For Quiet Detail Bundle Payload Fields

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Write failing API tests for quiet-detail fields**

Add tests to `WorkbenchApiTests` like:

```python
    def test_bundles_endpoint_exposes_quiet_enrichment_detail_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "detail-me"
            bundle.mkdir(parents=True)
            (bundle / "metadata.md").write_text(
                "---\n"
                "title: Detail Bundle\n"
                "primary_domain: ai-application\n"
                "conversion_status: converted\n"
                "review_required: false\n"
                "---\n",
                encoding="utf-8",
            )
            (bundle / "enrichment.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "summary": "這份資料主要在談 AI 工作流整理與知識維護。",
                        "primary_domain_suggestion": "ai-application",
                        "related_domains_suggestion": ["consulting"],
                        "topic_tags": ["knowledge-management", "workflow"],
                        "entity_hints": ["OpenAI", "Infinite Lore"],
                        "updated_at": "2026-04-12T00:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/bundles")

            self.assertEqual(response.status_code, 200)
            payload = response.json()[0]
            self.assertEqual(payload["enrichment_summary"], "這份資料主要在談 AI 工作流整理與知識維護。")
            self.assertEqual(payload["enrichment_primary_domain_suggestion"], "ai-application")
            self.assertEqual(payload["enrichment_related_domains_suggestion"], ["consulting"])
            self.assertEqual(payload["enrichment_topic_tags"], ["knowledge-management", "workflow"])
            self.assertEqual(payload["enrichment_entity_hints"], ["OpenAI", "Infinite Lore"])
            self.assertEqual(payload["enrichment_status_reason"], "")
```

and:

```python
    def test_bundles_endpoint_defaults_quiet_detail_fields_when_sidecar_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "plain-bundle"
            bundle.mkdir(parents=True)
            (bundle / "metadata.md").write_text(
                "---\n"
                "title: Plain Bundle\n"
                "primary_domain: ai-application\n"
                "conversion_status: converted\n"
                "review_required: false\n"
                "---\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/bundles")

            self.assertEqual(response.status_code, 200)
            payload = response.json()[0]
            self.assertEqual(payload["enrichment_summary"], "")
            self.assertEqual(payload["enrichment_primary_domain_suggestion"], "")
            self.assertEqual(payload["enrichment_related_domains_suggestion"], [])
            self.assertEqual(payload["enrichment_topic_tags"], [])
            self.assertEqual(payload["enrichment_entity_hints"], [])
            self.assertEqual(payload["enrichment_status_reason"], "")

    def test_bundles_endpoint_exposes_non_empty_enrichment_status_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "deferred-bundle"
            bundle.mkdir(parents=True)
            (bundle / "metadata.md").write_text(
                "---\n"
                "title: Deferred Bundle\n"
                "primary_domain: ai-application\n"
                "conversion_status: converted\n"
                "review_required: false\n"
                "---\n",
                encoding="utf-8",
            )
            (bundle / "enrichment.json").write_text(
                json.dumps(
                    {
                        "status": "deferred",
                        "status_reason": "這份資料暫時延後，因為目前尚未有可執行的增補路由。",
                        "failure_reason": "Provider 'ollama' is not supported by the minimal raw enrichment runner yet.",
                        "updated_at": "2026-04-12T00:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/bundles")

            self.assertEqual(response.status_code, 200)
            payload = response.json()[0]
            self.assertEqual(
                payload["enrichment_status_reason"],
                "這份資料暫時延後，因為目前尚未有可執行的增補路由。",
            )
```

- [ ] **Step 2: Run the focused tests to confirm RED**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_exposes_quiet_enrichment_detail_fields \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_defaults_quiet_detail_fields_when_sidecar_is_missing \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_exposes_non_empty_enrichment_status_reason -v
```

Expected:

- FAIL because `/api/bundles` does not expose the quiet-detail fields yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_workbench_api.py
git commit -m "test: add quiet enrichment detail bundle coverage"
```

## Task 2: Implement Quiet Detail Fields In Bundle Payloads

**Files:**
- Modify: `workbench/services.py`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Extend `_read_enrichment_payload` with quiet-detail fields**

Update `workbench/services.py` so `_read_enrichment_payload(...)` returns both the existing status fields and the quiet-detail content already present in `enrichment.json`:

```python
def _read_enrichment_payload(bundle_path: Path) -> Dict[str, object]:
    enrichment_path = bundle_path / "enrichment.json"
    empty_payload: Dict[str, object] = {
        "enrichment_status": "",
        "enrichment_provider": "",
        "enrichment_model": "",
        "enrichment_failure_reason": "",
        "enrichment_updated_at": "",
        "enrichment_summary": "",
        "enrichment_primary_domain_suggestion": "",
        "enrichment_related_domains_suggestion": [],
        "enrichment_topic_tags": [],
        "enrichment_entity_hints": [],
        "enrichment_status_reason": "",
    }
```

and, after validating the JSON object:

```python
    return {
        "enrichment_status": str(payload.get("status", "") or ""),
        "enrichment_provider": str(payload.get("provider", "") or ""),
        "enrichment_model": str(payload.get("model", "") or ""),
        "enrichment_failure_reason": str(payload.get("failure_reason", "") or ""),
        "enrichment_updated_at": str(payload.get("updated_at", "") or ""),
        "enrichment_summary": str(payload.get("summary", "") or ""),
        "enrichment_primary_domain_suggestion": str(payload.get("primary_domain_suggestion", "") or ""),
        "enrichment_related_domains_suggestion": _list_of_strings(payload.get("related_domains_suggestion")),
        "enrichment_topic_tags": _list_of_strings(payload.get("topic_tags")),
        "enrichment_entity_hints": _list_of_strings(payload.get("entity_hints")),
        "enrichment_status_reason": str(payload.get("status_reason") or ""),
    }
```

- [ ] **Step 2: Include the new fields in `list_bundles(...)` payloads**

Extend the bundle payload assembly:

```python
                "enrichment_status": enrichment["enrichment_status"],
                "enrichment_provider": enrichment["enrichment_provider"],
                "enrichment_model": enrichment["enrichment_model"],
                "enrichment_failure_reason": enrichment["enrichment_failure_reason"],
                "enrichment_updated_at": enrichment["enrichment_updated_at"],
                "enrichment_summary": enrichment["enrichment_summary"],
                "enrichment_primary_domain_suggestion": enrichment["enrichment_primary_domain_suggestion"],
                "enrichment_related_domains_suggestion": enrichment["enrichment_related_domains_suggestion"],
                "enrichment_topic_tags": enrichment["enrichment_topic_tags"],
                "enrichment_entity_hints": enrichment["enrichment_entity_hints"],
                "enrichment_status_reason": enrichment["enrichment_status_reason"],
                "enrichment_queue_active": bundle_path_text in active_enrichment_bundle_paths,
```

- [ ] **Step 3: Run the focused tests again**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_exposes_quiet_enrichment_detail_fields \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_defaults_quiet_detail_fields_when_sidecar_is_missing \
  tests.test_workbench_api.WorkbenchApiTests.test_bundles_endpoint_exposes_non_empty_enrichment_status_reason -v
```

Expected:

- PASS

- [ ] **Step 4: Run the broader Workbench API suite**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add workbench/services.py tests/test_workbench_api.py
git commit -m "feat: expose quiet enrichment detail bundle fields"
```

## Task 3: Add Red Tests For Inbox-Only Quiet Detail Rendering Contract

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add failing script-contract tests for preview and inline toggle behavior**

Append tests like:

```python
    def test_bundle_rendering_script_includes_quiet_detail_preview_and_toggle_labels(self) -> None:
        app_js_path = Path(__file__).resolve().parents[1] / "workbench" / "static" / "app.js"
        script = app_js_path.read_text(encoding="utf-8")

        render_bundles_start = script.index("function renderBundles()")
        self.assertIn("function formatBundleEnrichmentPreview(bundle)", script)
        self.assertIn("function buildBundleEnrichmentDetail(bundle)", script)
        self.assertIn("查看詳情", script[render_bundles_start:])
        self.assertIn("收起詳情", script[render_bundles_start:])
        self.assertIn("bundle-enrichment-detail", script[render_bundles_start:])
```

and:

```python
    def test_quiet_detail_script_keeps_summary_surface_read_only(self) -> None:
        app_js_path = Path(__file__).resolve().parents[1] / "workbench" / "static" / "app.js"
        script = app_js_path.read_text(encoding="utf-8")

        render_dashboard_start = script.index("function renderDashboard()")
        render_bundles_start = script.index("function renderBundles()", render_dashboard_start)
        dashboard_block = script[render_dashboard_start:render_bundles_start]

        self.assertNotIn("查看詳情", dashboard_block)
        self.assertNotIn("收起詳情", dashboard_block)
        self.assertNotIn("bundle-enrichment-detail", dashboard_block)
```

- [ ] **Step 2: Run the focused tests to confirm RED**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_bundle_rendering_script_includes_quiet_detail_preview_and_toggle_labels \
  tests.test_workbench_api.WorkbenchApiTests.test_quiet_detail_script_keeps_summary_surface_read_only -v
```

Expected:

- FAIL because the quiet-detail helpers and toggle labels do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_workbench_api.py
git commit -m "test: add inbox quiet detail rendering contract"
```

## Task 4: Implement Quiet Preview And Inline Detail In `收件匣`

**Files:**
- Modify: `workbench/static/app.js`
- Modify: `workbench/static/app.css`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add bundle-detail helper functions in `app.js`**

Near the existing top-level UI helpers, add:

```javascript
const expandedBundleDetails = new Set();

function joinHintList(items, limit = 3) {
  if (!Array.isArray(items) || !items.length) return "";
  return items
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean)
    .slice(0, limit)
    .join("、");
}

function formatBundleEnrichmentPreview(bundle) {
  const summary = typeof bundle?.enrichment_summary === "string" ? bundle.enrichment_summary.trim() : "";
  if (summary) return summary;

  const status = typeof bundle?.enrichment_status === "string" ? bundle.enrichment_status.trim() : "";
  const reason =
    typeof bundle?.enrichment_status_reason === "string" ? bundle.enrichment_status_reason.trim() : "";

  if (status === "deferred") {
    return "這份資料暫時延後，因為目前尚未有可執行的增補路由。";
  }
  if (status === "failed") {
    return reason ? `本次整理未完成：${reason}` : "本次整理未完成，可稍後再試。";
  }
  return "";
}

function buildBundleEnrichmentDetail(bundle) {
  const sections = [];
  const summary = typeof bundle?.enrichment_summary === "string" ? bundle.enrichment_summary.trim() : "";
  const primaryDomain =
    typeof bundle?.enrichment_primary_domain_suggestion === "string"
      ? bundle.enrichment_primary_domain_suggestion.trim()
      : "";
  const relatedDomains = joinHintList(bundle?.enrichment_related_domains_suggestion);
  const topicTags = joinHintList(bundle?.enrichment_topic_tags);
  const entityHints = joinHintList(bundle?.enrichment_entity_hints);
  const status = typeof bundle?.enrichment_status === "string" ? bundle.enrichment_status.trim() : "";
  const failureReason =
    typeof bundle?.enrichment_status_reason === "string" ? bundle.enrichment_status_reason.trim() : "";
  const updatedAt =
    typeof bundle?.enrichment_updated_at === "string" ? bundle.enrichment_updated_at.trim() : "";

  if (summary) sections.push(["整理摘要", summary]);
  if (primaryDomain || relatedDomains) {
    const domainLine = [primaryDomain, relatedDomains].filter(Boolean).join(" / ");
    if (domainLine) sections.push(["建議領域", domainLine]);
  }
  if (topicTags || entityHints) {
    const hintLine = [topicTags, entityHints].filter(Boolean).join(" / ");
    if (hintLine) sections.push(["主題與實體", hintLine]);
  }
  if ((status === "failed" || status === "deferred") && failureReason) {
    sections.push(["目前狀態說明", failureReason]);
  }
  if (updatedAt) sections.push(["最後更新", updatedAt]);
  return sections;
}

function bundleHasQuietDetail(bundle) {
  return Boolean(formatBundleEnrichmentPreview(bundle) || buildBundleEnrichmentDetail(bundle).length);
}
```

- [ ] **Step 2: Extend `renderBundles()` with low-noise preview and inline toggle**

Update `renderBundles()` so every row stays compact first, then optionally adds preview + detail:

```javascript
    const preview = formatBundleEnrichmentPreview(bundle);
    const detailSections = buildBundleEnrichmentDetail(bundle);
    const canExpand = detailSections.length > 0;
    const isExpanded = expandedBundleDetails.has(bundle.bundle_path);

    if (preview) {
      const previewLine = document.createElement("p");
      previewLine.className = "bundle-enrichment-preview";
      previewLine.textContent = preview;
      item.appendChild(previewLine);
    }

    if (canExpand) {
      const toggleRow = document.createElement("div");
      toggleRow.className = "bundle-enrichment-toggle-row";

      const toggleButton = document.createElement("button");
      toggleButton.type = "button";
      toggleButton.className = "ghost-button";
      toggleButton.textContent = isExpanded ? "收起詳情" : "查看詳情";
      toggleButton.addEventListener("click", () => {
        if (expandedBundleDetails.has(bundle.bundle_path)) {
          expandedBundleDetails.delete(bundle.bundle_path);
        } else {
          expandedBundleDetails.add(bundle.bundle_path);
        }
        renderBundles();
      });

      toggleRow.appendChild(toggleButton);
      item.appendChild(toggleRow);
    }

    if (isExpanded && detailSections.length) {
      const detailPanel = document.createElement("div");
      detailPanel.className = "bundle-enrichment-detail";
      const detailList = document.createElement("dl");

      detailSections.forEach(([label, value]) => {
        const row = document.createElement("div");
        const term = document.createElement("dt");
        const description = document.createElement("dd");
        term.textContent = label;
        description.textContent = value;
        row.append(term, description);
        detailList.appendChild(row);
      });

      detailPanel.appendChild(detailList);
      item.appendChild(detailPanel);
    }
```

Keep the existing retry / dismiss controls in the header block, and do **not** add any of this logic to `renderDashboard()`.

- [ ] **Step 3: Add restrained styles in `app.css`**

Add styles like:

```css
.bundle-enrichment-preview {
  margin: 0.65rem 0 0;
  color: var(--text);
  line-height: 1.65;
}

.bundle-enrichment-toggle-row {
  margin-top: 0.55rem;
  display: flex;
  justify-content: flex-start;
}

.bundle-enrichment-detail {
  margin-top: 0.75rem;
  padding: 0.9rem 1rem;
  border-radius: 0.9rem;
  background: color-mix(in srgb, var(--surface-alt) 72%, white 28%);
  border: 1px solid color-mix(in srgb, var(--line) 82%, white 18%);
}

.bundle-enrichment-detail dl {
  margin: 0;
  display: grid;
  gap: 0.7rem;
}

.bundle-enrichment-detail div {
  display: grid;
  gap: 0.2rem;
}

.bundle-enrichment-detail dt {
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.bundle-enrichment-detail dd {
  margin: 0;
  color: var(--text);
  line-height: 1.65;
}
```

- [ ] **Step 4: Run the focused script-contract tests again**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_bundle_rendering_script_includes_quiet_detail_preview_and_toggle_labels \
  tests.test_workbench_api.WorkbenchApiTests.test_quiet_detail_script_keeps_summary_surface_read_only -v
```

Expected:

- PASS

- [ ] **Step 5: Run `node --check` on the updated client script**

Run:

```bash
/Users/oldtien_base/.nvm/versions/node/v24.14.1/bin/node --check workbench/static/app.js
```

Expected:

- PASS

- [ ] **Step 6: Run the broader Workbench API suite again**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
```

Expected:

- PASS

- [ ] **Step 7: Commit**

```bash
git add workbench/static/app.js workbench/static/app.css tests/test_workbench_api.py
git commit -m "feat: add quiet enrichment detail in inbox"
```

## Task 5: Verify In Browser And Sync Docs

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-12-quiet-enrichment-detail-inbox-spec.md`
- Modify: `00_System/Home.md`

- [ ] **Step 1: Run live local browser verification for the quiet-detail slice**

Use the existing local QA posture with an isolated temp vault and local Workbench server.

Verify:

- `摘要` still only shows status-oriented recent imports
- `收件匣` rows remain readable at a glance
- completed bundles show a one-line quiet preview when summary data exists
- `查看詳情` expands only inside `收件匣`
- expanded detail shows result-and-reason information, not provider / model clutter
- existing `重試` / `清除` controls still work when the row is actionable

- [ ] **Step 2: Update the docs to match delivered behavior**

Update `00_System/Workflow Guide.md` to explain:

- quiet per-bundle enrichment preview now lives only in `收件匣`
- `摘要` remains overview-first
- expanded detail shows interpretation result and operator-meaningful reason, not backend internals

Update `docs/2026-04-12-quiet-enrichment-detail-inbox-spec.md`:

- change status to `Delivered and verified locally`
- add a short delivery note explaining the bounded inbox-only detail posture

Update `docs/2026-04-08-execution-roadmap.md`:

- add a completed section for the quiet-detail phase
- move `Current Next Action` to the next incomplete enrichment slice

Update `00_System/Home.md`:

- add the new implementation plan link beside the spec

- [ ] **Step 3: Run docs-phase verification**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

paths = [
    Path("docs/2026-04-12-quiet-enrichment-detail-inbox-spec.md"),
    Path("docs/2026-04-12-quiet-enrichment-detail-inbox-implementation-plan.md"),
]
markers = [
    "TO" + "DO",
    "TB" + "D",
    "implement " + "later",
    "fill in " + "details",
    "Similar to " + "Task",
]
hits = []
for path in paths:
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for marker in markers:
            if marker in line:
                hits.append(f"{path}:{line_no}:{marker}")
if hits:
    raise SystemExit("\n".join(hits))
PY
git diff --check
python3 tools/health_check.py .
```

Expected:

- no unresolved plan-marker hits
- no diff-check errors
- `Vault health check passed`

- [ ] **Step 4: Commit**

```bash
git add \
  00_System/Workflow\ Guide.md \
  00_System/Home.md \
  docs/2026-04-08-execution-roadmap.md \
  docs/2026-04-12-quiet-enrichment-detail-inbox-spec.md \
  docs/2026-04-12-quiet-enrichment-detail-inbox-implementation-plan.md
git commit -m "docs: sync quiet enrichment detail delivery"
```
