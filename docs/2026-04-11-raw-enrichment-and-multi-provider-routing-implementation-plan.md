# Raw Enrichment And Multi-Provider Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add background raw enrichment plus a route-driven multi-provider architecture where OpenAI shared-first is the active default and local providers are structurally supported without being required on day one.

**Architecture:** Keep `scan` and raw normalization deterministic, then add a bundle-local enrichment sidecar plus a background enrichment queue/state file. Introduce provider-aware route resolution in the Workbench settings/backend so `Ask` and `enrich_raw` can use OpenAI now while the config and execution model already supports future `Ollama` routing without redesigning the product later.

**Tech Stack:** Python 3.9, FastAPI, `unittest`, OpenAI Python SDK, existing Workbench settings API/UI, existing import and automation scan pipeline, local JSON config/state files

---

## File Structure

- Create: `workbench/provider_router.py`
  - normalize provider configs, resolve route preferences, and choose the active provider/model for a route
- Create: `tools/raw_enrichment.py`
  - raw enrichment queue runner, sidecar contract, OpenAI enrichment call, retry/status handling
- Modify: `workbench/config_store.py`
  - expand config schema to represent multiple providers and explicit `enrich_raw` routing
- Modify: `workbench/ask_service.py`
  - stop hard-coding `openai` inside route lookup and delegate to provider routing
- Modify: `workbench/services.py`
  - expose enrichment summary/status in bundle and dashboard responses where needed
- Modify: `workbench/server.py`
  - add any missing API hooks for settings schema expansion and enrichment visibility
- Modify: `workbench/static/index.html`
  - replace the single-provider settings form with a multi-provider settings surface
- Modify: `workbench/static/app.js`
  - load/save multiple providers and the new `enrich_raw` route without turning the homepage into a model cockpit
- Modify: `tools/import_bundle.py`
  - queue enrichment after successful raw bundle creation
- Modify: `tools/automation_scan.py`
  - queue enrichment after successful source ingestion while keeping scan/import success independent of model success
- Create: `tests/test_provider_router.py`
  - route/provider resolution coverage
- Create: `tests/test_raw_enrichment.py`
  - sidecar, queue, failure-state, and OpenAI shared-first enrichment coverage
- Modify: `tests/test_workbench_api.py`
  - settings API and inbox/bundle enrichment visibility tests
- Modify: `tests/test_query_ask.py`
  - Ask route resolution tests across multiple provider configs
- Modify after implementation: `00_System/Workflow Guide.md`
  - explain raw enrichment behavior and OpenAI shared-first routing
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark the phase delivered and move the next action forward
- Modify after implementation: `docs/2026-04-11-raw-enrichment-and-multi-provider-routing-spec.md`
  - update spec status from approved design to delivered behavior

This structure keeps the change bounded: provider routing lives in one backend module, raw enrichment lives in one background-processing module, and UI changes stay inside the existing settings surface.

## Task 1: Add Red Tests For Provider Routing And Config Shape

**Files:**
- Create: `tests/test_provider_router.py`
- Modify: `workbench/config_store.py`

- [ ] **Step 1: Write failing tests for multi-provider config defaults and route resolution**

Create `tests/test_provider_router.py` with:

```python
import unittest

from workbench.config_store import DEFAULT_CONFIG
from workbench.provider_router import resolve_route_provider


class ProviderRouterTests(unittest.TestCase):
    def test_default_config_includes_enrich_raw_route(self) -> None:
        self.assertEqual(DEFAULT_CONFIG["routes"]["enrich_raw"], "balanced")

    def test_openai_route_is_chosen_when_openai_provider_matches_role(self) -> None:
        settings = {
            "providers": [
                {
                    "id": "openai-main",
                    "provider": "openai",
                    "api_key": "sk-test",
                    "enabled": True,
                    "base_url": "",
                    "models": [
                        {"id": "gpt-5.4-mini", "role": "balanced"},
                        {"id": "gpt-5.4", "role": "best_deep"},
                    ],
                }
            ],
            "routes": {
                "ask": "best_deep",
                "enrich_raw": "balanced",
            },
            "route_provider_preferences": {},
        }

        route = resolve_route_provider(settings, "ask")

        self.assertEqual(route["provider"], "openai")
        self.assertEqual(route["model"], "gpt-5.4")

    def test_openai_is_preferred_when_local_provider_exists_but_is_not_enabled(self) -> None:
        settings = {
            "providers": [
                {
                    "id": "openai-main",
                    "provider": "openai",
                    "api_key": "sk-test",
                    "enabled": True,
                    "base_url": "",
                    "models": [{"id": "gpt-5.4-mini", "role": "balanced"}],
                },
                {
                    "id": "ollama-local",
                    "provider": "ollama",
                    "api_key": "",
                    "enabled": False,
                    "base_url": "http://127.0.0.1:11434",
                    "models": [{"id": "qwen3:14b", "role": "balanced"}],
                },
            ],
            "routes": {"enrich_raw": "balanced"},
            "route_provider_preferences": {"enrich_raw": ["openai-main", "ollama-local"]},
        }

        route = resolve_route_provider(settings, "enrich_raw")

        self.assertEqual(route["provider_id"], "openai-main")
        self.assertEqual(route["model"], "gpt-5.4-mini")

    def test_no_model_route_returns_none(self) -> None:
        settings = {
            "providers": [],
            "routes": {"scan": "no_model"},
            "route_provider_preferences": {},
        }

        self.assertIsNone(resolve_route_provider(settings, "scan"))
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_provider_router -v
```

Expected:

- FAIL because `workbench.provider_router` does not exist yet and `DEFAULT_CONFIG` does not yet include `enrich_raw`

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_provider_router.py workbench/config_store.py
git commit -m "test: cover multi-provider route resolution"
```

## Task 2: Implement Provider Routing And Config Defaults

**Files:**
- Create: `workbench/provider_router.py`
- Modify: `workbench/config_store.py`
- Modify: `tests/test_provider_router.py`

- [ ] **Step 1: Expand the default config schema**

Update `workbench/config_store.py` so `DEFAULT_CONFIG` becomes:

```python
DEFAULT_CONFIG: Dict[str, Any] = {
    "providers": [
        {
            "id": "openai-main",
            "provider": "openai",
            "enabled": True,
            "api_key": "",
            "base_url": "",
            "models": [
                {"id": "gpt-5.4-mini", "role": "balanced"},
                {"id": "gpt-5.4", "role": "best_deep"},
            ],
        }
    ],
    "routes": {
        "scan": "no_model",
        "import": "no_model",
        "enrich_raw": "balanced",
        "compile": "balanced",
        "ask": "best_deep",
        "query": "no_model",
        "reflection": "balanced",
    },
    "route_provider_preferences": {
        "ask": ["openai-main"],
        "enrich_raw": ["openai-main"],
        "compile": [],
        "reflection": ["openai-main"],
    },
}
```

- [ ] **Step 2: Implement the route resolver**

Create `workbench/provider_router.py` with:

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _provider_enabled(provider: Dict[str, Any]) -> bool:
    return provider.get("enabled") is not False


def _provider_can_run(provider: Dict[str, Any]) -> bool:
    provider_name = str(provider.get("provider") or "")
    if provider_name == "openai":
        return bool(str(provider.get("api_key") or "").strip())
    if provider_name == "ollama":
        return bool(str(provider.get("base_url") or "").strip())
    return False


def _models_for_role(provider: Dict[str, Any], role: str) -> Optional[str]:
    for model in provider.get("models", []):
        if model.get("role") == role and model.get("id"):
            return str(model["id"])
    return None


def resolve_route_provider(settings: Dict[str, Any], route_name: str) -> Optional[Dict[str, str]]:
    role = settings.get("routes", {}).get(route_name)
    if not role or role == "no_model":
        return None

    providers: List[Dict[str, Any]] = [provider for provider in settings.get("providers", []) if isinstance(provider, dict)]
    preferred_ids = settings.get("route_provider_preferences", {}).get(route_name, [])

    ordered: List[Dict[str, Any]] = []
    if isinstance(preferred_ids, list):
        for provider_id in preferred_ids:
            for provider in providers:
                if provider.get("id") == provider_id and provider not in ordered:
                    ordered.append(provider)
    for provider in providers:
        if provider not in ordered:
            ordered.append(provider)

    for provider in ordered:
        if not _provider_enabled(provider):
            continue
        if not _provider_can_run(provider):
            continue
        model_id = _models_for_role(provider, role)
        if not model_id:
            continue
        return {
            "provider_id": str(provider.get("id") or ""),
            "provider": str(provider.get("provider") or ""),
            "model": model_id,
            "api_key": str(provider.get("api_key") or ""),
            "base_url": str(provider.get("base_url") or ""),
        }
    return None
```

- [ ] **Step 3: Run the provider routing tests again**

Run:

```bash
python3 -m unittest tests.test_provider_router -v
```

Expected:

- PASS for the new provider-routing tests

- [ ] **Step 4: Commit**

```bash
git add workbench/config_store.py workbench/provider_router.py tests/test_provider_router.py
git commit -m "feat: add multi-provider route resolution"
```

## Task 3: Add Red Tests For Settings UI Multi-Provider Behavior

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add failing API tests for multi-provider settings persistence**

Append tests like these to `tests/test_workbench_api.py`:

```python
    def test_settings_round_trip_preserves_multiple_providers_and_enrich_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            client = self.make_client(root, config_path)

            payload = {
                "providers": [
                    {
                        "id": "openai-main",
                        "provider": "openai",
                        "enabled": True,
                        "api_key": "sk-test",
                        "base_url": "",
                        "models": [
                            {"id": "gpt-5.4-mini", "role": "balanced"},
                            {"id": "gpt-5.4", "role": "best_deep"},
                        ],
                    },
                    {
                        "id": "ollama-local",
                        "provider": "ollama",
                        "enabled": False,
                        "api_key": "",
                        "base_url": "http://127.0.0.1:11434",
                        "models": [
                            {"id": "qwen3:14b", "role": "balanced"},
                            {"id": "gemma4:26b", "role": "best_deep"},
                        ],
                    },
                ],
                "routes": {
                    "scan": "no_model",
                    "import": "no_model",
                    "enrich_raw": "balanced",
                    "compile": "balanced",
                    "query": "no_model",
                    "ask": "best_deep",
                    "reflection": "balanced",
                },
                "route_provider_preferences": {
                    "ask": ["openai-main", "ollama-local"],
                    "enrich_raw": ["openai-main"],
                    "compile": ["ollama-local", "openai-main"],
                },
            }

            response = client.post("/api/settings", json=payload)
            self.assertEqual(response.status_code, 200)
            round_trip = client.get("/api/settings")
            self.assertEqual(round_trip.status_code, 200)
            saved = round_trip.json()
            self.assertEqual(len(saved["providers"]), 2)
            self.assertEqual(saved["routes"]["enrich_raw"], "balanced")
            self.assertEqual(saved["route_provider_preferences"]["compile"][0], "ollama-local")
```

- [ ] **Step 2: Run the targeted API test to confirm it fails**

Run:

```bash
python3 -m unittest tests.test_workbench_api.WorkbenchApiTests.test_settings_round_trip_preserves_multiple_providers_and_enrich_route -v
```

Expected:

- FAIL because current config persistence and defaults do not yet fully support the richer provider schema

- [ ] **Step 3: Commit the red test**

```bash
git add tests/test_workbench_api.py
git commit -m "test: cover multi-provider settings persistence"
```

## Task 4: Implement Multi-Provider Settings UI And API Contract

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Replace the single-provider settings form with a provider list**

Update the settings area in `workbench/static/index.html` so the provider section becomes:

```html
<section class="panel">
  <div class="panel-head">
    <div>
      <p class="eyebrow">模型供應商</p>
      <h3>多供應商設定</h3>
    </div>
  </div>
  <div id="providerList" class="list-stack"></div>
  <div class="button-row">
    <button id="addProviderButton" type="button" class="ghost-button">新增供應商</button>
  </div>
</section>
```

Add a new route selector for `enrich_raw` beside the existing route controls:

```html
<label><span>原始資料整理</span><select id="routeEnrichRaw"><option value="no_model">不使用模型</option><option value="balanced" selected>平衡</option><option value="best_deep">高品質</option></select></label>
```

- [ ] **Step 2: Add provider rendering and save logic in `workbench/static/app.js`**

Add helper logic like:

```javascript
function normalizeProvider(provider, index) {
  return {
    id: provider?.id || `provider-${index + 1}`,
    provider: provider?.provider || "openai",
    enabled: provider?.enabled !== false,
    api_key: provider?.api_key || "",
    base_url: provider?.base_url || "",
    models: Array.isArray(provider?.models) ? provider.models : [],
  };
}

function renderProviders() {
  const container = document.getElementById("providerList");
  const providers = Array.isArray(state.settings?.providers) ? state.settings.providers : [];
  container.innerHTML = "";
  providers.forEach((provider, index) => {
    const normalized = normalizeProvider(provider, index);
    const card = document.createElement("article");
    card.className = "list-item";
    card.innerHTML = `
      <label><span>供應商類型</span><input data-provider-index="${index}" data-field="provider" value="${normalized.provider}" /></label>
      <label><span>供應商 ID</span><input data-provider-index="${index}" data-field="id" value="${normalized.id}" /></label>
      <label><span>API 金鑰</span><input type="password" data-provider-index="${index}" data-field="api_key" value="${normalized.api_key}" /></label>
      <label><span>Base URL</span><input data-provider-index="${index}" data-field="base_url" value="${normalized.base_url}" /></label>
    `;
    container.appendChild(card);
  });
}
```

Update the settings submit handler so the payload includes:

```javascript
routes: {
  scan: document.getElementById("routeScan").value,
  import: document.getElementById("routeImport").value,
  enrich_raw: document.getElementById("routeEnrichRaw").value,
  compile: document.getElementById("routeCompile").value,
  query: document.getElementById("routeQuery").value,
  ask: document.getElementById("routeAsk").value,
  reflection: document.getElementById("routeReflection").value,
},
route_provider_preferences: {
  ask: ["openai-main"],
  enrich_raw: ["openai-main"],
  compile: ["ollama-local", "openai-main"],
}
```

- [ ] **Step 3: Run the targeted settings API/UI tests**

Run:

```bash
python3 -m unittest tests.test_workbench_api.WorkbenchApiTests.test_settings_round_trip_preserves_multiple_providers_and_enrich_route -v
/Users/oldtien_base/.nvm/versions/node/v24.14.1/bin/node --check workbench/static/app.js
```

Expected:

- API test passes
- `app.js` syntax check passes

- [ ] **Step 4: Commit**

```bash
git add workbench/static/index.html workbench/static/app.js tests/test_workbench_api.py
git commit -m "feat: add multi-provider settings model"
```

## Task 5: Add Red Tests For Raw Enrichment Queue And Sidecar State

**Files:**
- Create: `tests/test_raw_enrichment.py`
- Modify: `tools/import_bundle.py`
- Modify: `tools/automation_scan.py`

- [ ] **Step 1: Write failing tests for queueing and sidecar behavior**

Create `tests/test_raw_enrichment.py` with:

```python
import json
import tempfile
import unittest
from pathlib import Path

from tools.raw_enrichment import default_enrichment_path, default_enrichment_state_path, queue_bundle_for_enrichment


class RawEnrichmentTests(unittest.TestCase):
    def test_queue_bundle_marks_pending_and_records_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw/inbox/2026-04-11-example"
            bundle.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle)

            enrichment_path = default_enrichment_path(bundle)
            state_path = default_enrichment_state_path(root)
            self.assertTrue(enrichment_path.exists())
            self.assertTrue(state_path.exists())

            enrichment = json.loads(enrichment_path.read_text(encoding="utf-8"))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(enrichment["status"], "pending")
            self.assertEqual(state["pending_bundles"][0]["bundle_path"], bundle.relative_to(root).as_posix())
```

- [ ] **Step 2: Run the new raw enrichment tests and confirm they fail**

Run:

```bash
python3 -m unittest tests.test_raw_enrichment -v
```

Expected:

- FAIL because `tools.raw_enrichment` does not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_raw_enrichment.py tools/import_bundle.py tools/automation_scan.py
git commit -m "test: cover raw enrichment queue state"
```

## Task 6: Implement Raw Enrichment Queue And OpenAI Shared-First Enrichment

**Files:**
- Create: `tools/raw_enrichment.py`
- Modify: `tools/import_bundle.py`
- Modify: `tools/automation_scan.py`
- Modify: `workbench/services.py`
- Modify: `tests/test_raw_enrichment.py`

- [ ] **Step 1: Create the raw enrichment module**

Create `tools/raw_enrichment.py` with:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from workbench.config_store import load_config
from workbench.provider_router import resolve_route_provider

ENRICHMENT_FILENAME = "enrichment.json"
ENRICHMENT_STATE_FILENAME = "raw-enrichment-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_enrichment_path(bundle_path: Path) -> Path:
    return bundle_path / ENRICHMENT_FILENAME


def default_enrichment_state_path(root: Path) -> Path:
    return root / "00_System" / ENRICHMENT_STATE_FILENAME


def queue_bundle_for_enrichment(root: Path, bundle_path: Path) -> None:
    enrichment_path = default_enrichment_path(bundle_path)
    enrichment_path.write_text(
        json.dumps(
            {
                "status": "pending",
                "provider": "",
                "model": "",
                "started_at": "",
                "completed_at": "",
                "failure_reason": "",
                "primary_domain_suggestion": "",
                "related_domains_suggestion": [],
                "summary": "",
                "topic_tags": [],
                "entity_hints": [],
                "quality_flags": [],
                "wiki_update_hint": "",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    state_path = default_enrichment_state_path(root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pending_bundles": []}
    if state_path.exists():
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload.setdefault("pending_bundles", []).append(
        {"bundle_path": bundle_path.relative_to(root).as_posix(), "queued_at": now_iso()}
    )
    state_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def enrich_bundle(root: Path, bundle_path: Path, settings_path: Path) -> Dict[str, Any]:
    settings = load_config(settings_path)
    route = resolve_route_provider(settings, "enrich_raw")
    if not route or route["provider"] != "openai":
        return {"status": "skipped", "reason": "no_openai_route"}

    metadata_path = bundle_path / "metadata.md"
    content_path = bundle_path / "content.md"
    content = content_path.read_text(encoding="utf-8") if content_path.exists() else ""
    prompt = (
        "You are enriching raw knowledge captures for a personal LLM wiki. "
        "Return compact JSON with primary_domain_suggestion, related_domains_suggestion, summary, "
        "topic_tags, entity_hints, quality_flags, wiki_update_hint."
        f"\\n\\nRaw content:\\n{content[:8000]}"
    )

    client = OpenAI(api_key=route["api_key"])
    response = client.responses.create(model=route["model"], input=prompt)
    output = response.output_text.strip()
    payload = json.loads(output)
    payload.update(
        {
            "status": "completed",
            "provider": route["provider"],
            "model": route["model"],
            "started_at": now_iso(),
            "completed_at": now_iso(),
            "failure_reason": "",
        }
    )
    default_enrichment_path(bundle_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
```

- [ ] **Step 2: Queue enrichment after raw import and scan ingestion**

In `tools/import_bundle.py`, after the raw bundle is fully written and before optional compile, add:

```python
from tools.raw_enrichment import queue_bundle_for_enrichment
```

and then:

```python
queue_bundle_for_enrichment(root, bundle)
```

In `tools/automation_scan.py`, after successful import of a candidate bundle, also call `queue_bundle_for_enrichment(...)`.

- [ ] **Step 3: Run the raw enrichment tests**

Run:

```bash
python3 -m unittest tests.test_raw_enrichment -v
```

Expected:

- PASS for queue/sidecar state tests

- [ ] **Step 4: Commit**

```bash
git add tools/raw_enrichment.py tools/import_bundle.py tools/automation_scan.py tests/test_raw_enrichment.py
git commit -m "feat: add raw enrichment queue"
```

## Task 7: Route Ask Through Provider Abstraction And Verify OpenAI Shared-First Behavior

**Files:**
- Modify: `workbench/ask_service.py`
- Modify: `tests/test_query_ask.py`
- Modify: `tests/test_provider_router.py`

- [ ] **Step 1: Replace the OpenAI-only route lookup**

Update `workbench/ask_service.py` so:

```python
from workbench.provider_router import resolve_route_provider
```

and replace:

```python
route = resolve_route_model(settings, "ask")
```

with:

```python
route = resolve_route_provider(settings, "ask")
```

Then guard the generator call:

```python
if route and route["provider"] == "openai":
    generator = generate_answer or (lambda **kwargs: openai_answer(**kwargs))
    answer = generator(
        question=question,
        grounding=grounding,
        model=route["model"],
        api_key=route["api_key"],
    )
```

- [ ] **Step 2: Add and run Ask routing tests**

Append tests like:

```python
    def test_ask_mode_prefers_openai_route_when_openai_is_first_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="What is knowledge compilation?",
                requested_mode="ask",
                settings={
                    "providers": [
                        {
                            "id": "openai-main",
                            "provider": "openai",
                            "enabled": True,
                            "api_key": "sk-test",
                            "base_url": "",
                            "models": [{"id": "gpt-5.4", "role": "best_deep"}],
                        },
                        {
                            "id": "ollama-local",
                            "provider": "ollama",
                            "enabled": True,
                            "api_key": "",
                            "base_url": "http://127.0.0.1:11434",
                            "models": [{"id": "gemma4:26b", "role": "best_deep"}],
                        },
                    ],
                    "routes": {"query": "no_model", "ask": "best_deep"},
                    "route_provider_preferences": {"ask": ["openai-main", "ollama-local"]},
                },
                generate_answer=lambda **kwargs: "MODEL ANSWER",
            )

            self.assertEqual(result["answer"], "MODEL ANSWER")
            self.assertEqual(result["answer_source"], "model")
```

Run:

```bash
python3 -m unittest tests.test_query_ask tests.test_provider_router -v
```

Expected:

- all Ask/provider routing tests pass

- [ ] **Step 3: Commit**

```bash
git add workbench/ask_service.py tests/test_query_ask.py tests/test_provider_router.py
git commit -m "feat: route ask through provider abstraction"
```

## Task 8: Sync Docs And Run Full Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-11-raw-enrichment-and-multi-provider-routing-spec.md`

- [ ] **Step 1: Update the user-facing docs**

Update `00_System/Workflow Guide.md` to add:

```md
## Raw Enrichment

- new raw bundles are preserved first
- a background enrichment job is then queued automatically
- enrichment writes a bundle-local `enrichment.json` sidecar
- enrichment failure does not block raw preservation or later reprocessing
- current default model strategy:
  - `Ask` -> OpenAI shared-first
  - `raw enrichment` -> OpenAI shared-first
  - `scan / RSS / web capture` -> no model
  - local provider architecture exists for later Ollama-based compile / rewrite work
```

Update `docs/2026-04-11-raw-enrichment-and-multi-provider-routing-spec.md` status to:

```md
**Status:** Delivered and verified locally
```

Update `docs/2026-04-08-execution-roadmap.md` so it records the delivered phase and moves the next action to the next planning target.

- [ ] **Step 2: Run full verification**

Run:

```bash
python3 -m unittest tests.test_provider_router tests.test_raw_enrichment tests.test_query_ask tests.test_workbench_api tests.test_app_shell -v
python3 tools/health_check.py .
/Users/oldtien_base/.nvm/versions/node/v24.14.1/bin/node --check workbench/static/app.js
git diff --check
```

Expected:

- all targeted tests pass
- health check passes
- frontend syntax check passes
- diff check passes

- [ ] **Step 3: Commit docs sync**

```bash
git add \
  00_System/Workflow\ Guide.md \
  docs/2026-04-08-execution-roadmap.md \
  docs/2026-04-11-raw-enrichment-and-multi-provider-routing-spec.md
git commit -m "docs: sync raw enrichment and routing delivery"
```
