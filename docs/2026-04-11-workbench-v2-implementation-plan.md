# Workbench V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Workbench into a desktop-first, Traditional Chinese-first, Ask-first product surface whose homepage becomes the real daily knowledge workspace.

**Architecture:** Keep the existing local Python backend and vault contract intact while rebuilding the frontend shell, homepage IA, and visual hierarchy around `首頁 = Ask 工作台`. Reuse the current ask, inbox, knowledge, and system data flows instead of reopening backend architecture, and shift the UI from an equal-page localhost tool into a reading-first macOS-style workstation shell.

**Tech Stack:** Python 3.9, FastAPI, `unittest`, vanilla HTML/CSS/JavaScript, existing Workbench backend, existing Ask/Reflection/Automation flows, browser QA through the local Workbench runtime

---

## File Structure

- Modify: `tests/test_workbench_api.py`
  - add static shell contract tests for Traditional Chinese navigation and the new homepage role
- Modify: `workbench/static/index.html`
  - rebuild the shell IA and homepage markup
- Modify: `workbench/static/app.js`
  - update navigation titles, page routing, and homepage rendering assumptions
- Modify: `workbench/static/app.css`
  - apply the desktop-first visual system and new top/middle/bottom layout
- Modify after implementation: `00_System/Workflow Guide.md`
  - describe the new Workbench V2 page model
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark Workbench V2 as delivered once it is real
- Modify after implementation: `docs/2026-04-10-workbench-v2-design-spec.md`
  - update the status from approved design to delivered behavior

This structure keeps V2 focused on the surface layer: page roles, shell behavior, layout, copy, and verification. The backend contract remains stable.

## Task 1: Add Red Tests For The New Workbench Shell Contract

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add failing root-shell tests**

Append tests like:

```python
    def test_root_html_uses_traditional_chinese_primary_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            html = response.text
            self.assertIn('lang="zh-Hant"', html)
            for label in ("首頁", "摘要", "收件匣", "知識庫", "系統", "設定"):
                self.assertIn(f">{label}<", html)
            self.assertIn('data-page="summary"', html)
            self.assertNotIn('data-page="ask"', html)

    def test_root_html_makes_home_the_ask_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            html = response.text
            self.assertIn("首頁工作台", html)
            self.assertIn("圖書館答案", html)
            self.assertIn("證據與脈絡", html)
            self.assertIn("我的工作區", html)
            self.assertIn("摘要", html)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_uses_traditional_chinese_primary_navigation \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_makes_home_the_ask_workspace \
  -v
```

Expected:

- FAIL because the current Workbench still uses English primary navigation and still exposes `Ask` as a separate top-level page

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_workbench_api.py
git commit -m "test: add workbench v2 shell coverage"
```

## Task 2: Implement The New IA Shell And Traditional Chinese Navigation

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`
- Test: `tests/test_workbench_api.py`

- [ ] **Step 1: Replace the sidebar navigation labels and page model**

Update the navigation block in `workbench/static/index.html` to:

```html
<nav class="nav">
  <button class="nav-link active" data-page="home">首頁</button>
  <button class="nav-link" data-page="summary">摘要</button>
  <button class="nav-link" data-page="inbox">收件匣</button>
  <button class="nav-link" data-page="knowledge">知識庫</button>
  <button class="nav-link" data-page="system">系統</button>
  <button class="nav-link" data-page="settings">設定</button>
</nav>
```

Also change the document root to:

```html
<html lang="zh-Hant">
```

- [ ] **Step 2: Add a real page-title map in `workbench/static/app.js`**

Replace the current `setPage()` title logic with:

```javascript
const PAGE_TITLES = {
  home: "首頁",
  summary: "摘要",
  inbox: "收件匣",
  knowledge: "知識庫",
  system: "系統",
  settings: "設定",
};

function setPage(page) {
  state.page = page;
  pages.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  navLinks.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  pageTitle.textContent = PAGE_TITLES[page] || "首頁";
}
```

- [ ] **Step 3: Remove the separate top-level `Ask` page**

Delete the `data-page="ask"` navigation entry and repurpose the old dashboard-style `home` page into a new `summary` page.

The old dashboard region should become:

```html
<section class="page" data-page="summary">
  <div class="grid two-col">
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">最近匯入</p>
          <h3>原始資料活動</h3>
        </div>
      </div>
      <div id="recentImports" class="list-stack empty-state">載入中…</div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">最近知識</p>
          <h3>最新編譯結果</h3>
        </div>
      </div>
      <div id="recentKnowledge" class="list-stack empty-state">載入中…</div>
    </section>
  </div>
  <div class="grid three-col" id="snapshotCards"></div>
</section>
```

- [ ] **Step 4: Re-run the targeted tests and a JS syntax check**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_uses_traditional_chinese_primary_navigation \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_makes_home_the_ask_workspace \
  -v
node --check workbench/static/app.js
```

Expected:

- both Python tests PASS
- `node --check` exits successfully

- [ ] **Step 5: Commit**

```bash
git add workbench/static/index.html workbench/static/app.js tests/test_workbench_api.py
git commit -m "feat: reset workbench v2 shell ia"
```

## Task 3: Add Red Tests For The Homepage Workspace Regions

**Files:**
- Modify: `tests/test_workbench_api.py`

- [ ] **Step 1: Add failing homepage-structure tests**

Append tests like:

```python
    def test_root_html_homepage_uses_top_middle_bottom_workspace_regions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            html = response.text
            self.assertIn("精簡提問列", html)
            self.assertIn("圖書館答案", html)
            self.assertIn("證據與脈絡", html)
            self.assertIn("我的工作區", html)

    def test_root_html_keeps_reflection_and_correction_outside_the_answer_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            html = response.text
            self.assertIn("最近反思", html)
            self.assertIn("修正知識", html)
            self.assertIn("草稿審閱", html)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_homepage_uses_top_middle_bottom_workspace_regions \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_keeps_reflection_and_correction_outside_the_answer_block \
  -v
```

Expected:

- FAIL because the current homepage does not yet implement the top/middle/bottom V2 workspace contract

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_workbench_api.py
git commit -m "test: add homepage workspace coverage"
```

## Task 4: Implement The Homepage Ask Workspace And Summary Relocation

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.js`
- Modify: `workbench/static/app.css`
- Test: `tests/test_workbench_api.py`

- [ ] **Step 1: Rebuild `首頁` as the main Ask workspace in `workbench/static/index.html`**

Replace the old `home` section with a top/middle/bottom structure like:

```html
<section class="page active" data-page="home">
  <section class="panel workspace-top">
    <div class="panel-head">
      <div>
        <p class="eyebrow">首頁工作台</p>
        <h3>提出問題</h3>
      </div>
    </div>
    <form id="askForm" class="stack-form compact-ask-form">
      <label>
        <span>問題</span>
        <textarea id="askInput" placeholder="直接從你的知識庫提問。"></textarea>
      </label>
      <div class="button-row">
        <label class="inline-select">
          <span>模式</span>
          <select id="askMode">
            <option value="auto">自動</option>
            <option value="ask">問答</option>
            <option value="query">查詢</option>
          </select>
        </label>
        <button id="askSubmitButton" type="submit" class="primary-button">詢問知識庫</button>
      </div>
    </form>
  </section>

  <section class="panel workspace-answer">
    <div class="panel-head">
      <div>
        <p class="eyebrow">圖書館答案</p>
        <h3>主要回答</h3>
      </div>
    </div>
    <div id="askAnswer" class="empty-state">提出問題後，來源導向的回答會顯示在這裡。</div>
    <div class="workspace-limits">
      <p class="eyebrow">限制與不確定性</p>
      <div id="askLimits" class="list-stack empty-state">需要時才會顯示在這裡。</div>
    </div>
  </section>

  <section class="panel workspace-evidence">
    <div class="panel-head">
      <div>
        <p class="eyebrow">證據與脈絡</p>
        <h3>為什麼可以相信這個答案</h3>
      </div>
    </div>
    <div class="grid evidence-stack">
      <section>
        <p class="eyebrow">Grounding</p>
        <div id="askGrounding" class="list-stack empty-state">Grounding 會顯示在這裡。</div>
      </section>
      <section>
        <p class="eyebrow">來源脈絡</p>
        <div id="askTrace" class="list-stack empty-state">來源脈絡會顯示在這裡。</div>
      </section>
      <section>
        <p class="eyebrow">關聯脈絡</p>
        <div id="askRelationTrace" class="list-stack empty-state">關聯脈絡會顯示在這裡。</div>
      </section>
    </div>
  </section>

  <section class="panel workspace-followup">
    <div class="panel-head">
      <div>
        <p class="eyebrow">我的工作區</p>
        <h3>反思、修正與草稿審閱</h3>
      </div>
    </div>
    <div class="grid followup-stack">
      <section>
        <p class="eyebrow">最近反思</p>
        <div id="reflectionList" class="list-stack empty-state">先詢問知識庫，再從這裡查看最近反思。</div>
      </section>
      <section>
        <p class="eyebrow">修正知識</p>
        <textarea id="feedbackInput" placeholder="輸入修正要求或你的詮釋。"></textarea>
        <div class="button-row">
          <button id="draftCorrectionButton" type="button" class="primary-button">修正知識</button>
          <button id="draftReflectionButton" type="button" class="secondary-button">加入詮釋</button>
        </div>
      </section>
      <section>
        <p class="eyebrow">草稿審閱</p>
        <div id="feedbackEditorEmpty" class="empty-state">在上方建立草稿後，這裡會出現審閱內容。</div>
        <div id="feedbackEditorBody" class="stack-form" hidden>
          <div id="feedbackEditorMeta" class="list-stack"></div>
          <label>
            <span>草稿內容</span>
            <textarea id="feedbackEditorTextarea"></textarea>
          </label>
          <div class="button-row">
            <button id="feedbackConfirmButton" type="button" class="primary-button">確認</button>
            <button id="feedbackDiscardButton" type="button" class="ghost-button">放棄</button>
          </div>
        </div>
      </section>
    </div>
  </section>
</section>
```

- [ ] **Step 2: Keep the existing ask / reflection JS IDs but remove the old page assumptions**

Update the old home-ask redirect behavior in `workbench/static/app.js` so the homepage itself is the Ask surface.

Replace the old submit bridge:

```javascript
document.getElementById("homeAskForm").addEventListener("submit", (event) => {
  event.preventDefault();
  document.getElementById("askInput").value = document.getElementById("homeAskInput").value;
  setPage("ask");
  runAsk(document.getElementById("askInput").value, "auto");
});
```

with:

```javascript
document.getElementById("askForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await runAsk(document.getElementById("askInput").value, document.getElementById("askMode").value);
});
```

Also remove any assumptions that `ask` is a separate page key.

- [ ] **Step 3: Add the new desktop-first homepage layout styles**

Add CSS blocks like:

```css
.workspace-top,
.workspace-answer,
.workspace-evidence,
.workspace-followup {
  padding: 1.35rem;
}

.compact-ask-form textarea {
  min-height: 5.75rem;
}

.workspace-answer {
  min-height: 22rem;
}

.evidence-stack,
.followup-stack {
  grid-template-columns: 1fr;
}

.workspace-limits {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid color-mix(in srgb, var(--line) 70%, white 30%);
}
```

The key is:

- top prompt stays compact
- answer gets the largest reading width
- evidence and follow-up work stack vertically below

- [ ] **Step 4: Re-run the homepage-structure tests and JS syntax check**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_homepage_uses_top_middle_bottom_workspace_regions \
  tests.test_workbench_api.WorkbenchApiTests.test_root_html_keeps_reflection_and_correction_outside_the_answer_block \
  -v
node --check workbench/static/app.js
```

Expected:

- both Python tests PASS
- `node --check` exits successfully

- [ ] **Step 5: Commit**

```bash
git add workbench/static/index.html workbench/static/app.js workbench/static/app.css tests/test_workbench_api.py
git commit -m "feat: redesign workbench v2 homepage"
```

## Task 5: Apply The Desktop-First Visual System Across The Shell

**Files:**
- Modify: `workbench/static/index.html`
- Modify: `workbench/static/app.css`
- Modify: `workbench/static/app.js`

- [ ] **Step 1: Replace the current copy and chrome with a calmer Traditional Chinese shell**

Update shell-level copy in `workbench/static/index.html` such as:

```html
<div class="brand">
  <div class="brand-mark">IL</div>
  <div>
    <p class="eyebrow">Infinite Lore</p>
    <h1>知識工作台</h1>
  </div>
</div>

<header class="topbar">
  <div>
    <p class="eyebrow">共享知識庫</p>
    <h2 id="pageTitle">首頁</h2>
  </div>
  <div class="status-pill" id="healthPill">檢查系統狀態中…</div>
</header>
```

- [ ] **Step 2: Replace the visual tokens with the V2 consultant-reading style**

Update the top of `workbench/static/app.css` to something like:

```css
:root {
  color-scheme: light;
  --bg: #f6f8fb;
  --bg-strong: #eef2f7;
  --surface: #ffffff;
  --surface-alt: #f8fafc;
  --line: #d7dee8;
  --text: #182230;
  --muted: #5f6b7a;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --ok: #15803d;
  --warn: #d97706;
  --shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  --radius: 20px;
}

body {
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 28rem),
    linear-gradient(180deg, var(--bg), var(--bg-strong));
  color: var(--text);
  font-family: "Atkinson Hyperlegible", "Manrope", sans-serif;
}
```

Also update the font imports in `workbench/static/index.html` to:

```html
<link
  href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap"
  rel="stylesheet"
/>
```

- [ ] **Step 3: Make the shell feel application-like rather than webpage-like**

Adjust the shell sizing and sidebar rhythm:

```css
.shell {
  display: grid;
  grid-template-columns: 17rem 1fr;
  min-height: 100vh;
}

.sidebar {
  padding: 1.5rem 1.25rem;
  background: rgba(255, 255, 255, 0.92);
  border-right: 1px solid var(--line);
  backdrop-filter: blur(18px);
}

.main {
  padding: 1.5rem 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
```

Keep the mobile fallback vertical:

```css
@media (max-width: 1040px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}
```

- [ ] **Step 4: Run static and server smoke checks**

Run:

```bash
python3 -m unittest tests.test_workbench_api -v
node --check workbench/static/app.js
```

Expected:

- Workbench API tests PASS
- JS syntax check PASS

- [ ] **Step 5: Commit**

```bash
git add workbench/static/index.html workbench/static/app.css workbench/static/app.js tests/test_workbench_api.py
git commit -m "feat: apply workbench v2 visual system"
```

## Task 6: Sync Docs And Run Final Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-10-workbench-v2-design-spec.md`

- [ ] **Step 1: Update docs to match shipped Workbench V2 behavior**

Add or revise sections so they explicitly describe:

- `首頁 = Ask 工作台`
- `摘要` as the former dashboard-like overview page
- Traditional Chinese primary navigation
- the top/middle/bottom homepage structure
- desktop-first shell posture for the current local Workbench

Use wording like:

```md
## Workbench V2

Workbench V2 now uses:

- `首頁` as the main Ask workspace
- `摘要` for recent activity and operational snapshot
- Traditional Chinese primary navigation
- a top / middle / bottom homepage layout:
  - compact prompt bar
  - wide answer surface
  - evidence region
  - personal follow-up work region
```

- [ ] **Step 2: Run the focused regression suite**

Run:

```bash
python3 -m unittest \
  tests.test_workbench_api \
  tests.test_vision_ocr \
  tests.test_image_adapter \
  tests.test_import_bundle \
  tests.test_multimodal_detect \
  tests.test_wiki_compile \
  tests.test_query_ask \
  -v
```

Expected:

- PASS

- [ ] **Step 3: Run the JS syntax and health checks**

Run:

```bash
node --check workbench/static/app.js
python3 tools/health_check.py .
```

Expected:

- `node --check` exits successfully
- `Vault health check passed`

- [ ] **Step 4: Run the local Workbench once and confirm the shell loads**

Run:

```bash
python3 tools/run_workbench.py
```

Expected:

- local server starts on `127.0.0.1:8765`

Then, in a second terminal:

```bash
curl http://127.0.0.1:8765 | head -40
```

Expected:

- output contains `首頁`
- output contains `摘要`
- output contains `圖書館答案`

- [ ] **Step 5: Commit**

```bash
git add 00_System/Workflow\ Guide.md docs/2026-04-08-execution-roadmap.md docs/2026-04-10-workbench-v2-design-spec.md
git commit -m "docs: sync workbench v2 rollout"
```

## Self-Review

### Spec coverage

- Ask-first homepage: covered by Tasks 1 through 4
- `摘要` replacing the old home dashboard: covered by Task 2
- Traditional Chinese primary UI: covered by Tasks 1, 2, and 5
- top/middle/bottom homepage structure: covered by Tasks 3 and 4
- desktop-first visual system: covered by Task 5
- docs and verification: covered by Task 6

### Placeholder scan

- no `TODO`
- no `TBD`
- no “implement later” language
- no unresolved page-name ambiguity remains

### Type consistency

- `summary` is used consistently as the replacement page key for the old dashboard-like home surface
- `PAGE_TITLES` aligns with the new navigation labels
- homepage regions are consistently named as prompt / answer / evidence / follow-up work
