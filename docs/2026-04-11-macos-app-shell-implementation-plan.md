# macOS App Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the delivered Workbench V2 into a single-window macOS desktop app that starts the local server automatically and hides localhost, browser, and terminal from the normal user flow.

**Architecture:** Keep the existing FastAPI Workbench and vault contract intact. Add a small Python desktop shell layer that manages an embedded local server lifecycle, waits for readiness, and opens the Workbench inside a `pywebview` macOS window. Package that shell with PyInstaller as a local `.app` bundle rather than replacing the current browser-based architecture.

**Tech Stack:** Python 3.9, FastAPI, `uvicorn`, `httpx`, `unittest`, `pywebview`, `PyInstaller`, existing Workbench backend and static frontend

---

## File Structure

- Modify: `requirements.txt`
  - add the runtime desktop dependency needed for the app shell
- Create: `app_shell/__init__.py`
  - mark the desktop shell package
- Create: `app_shell/runtime.py`
  - embedded FastAPI server lifecycle, free-port binding, readiness polling, shutdown
- Create: `app_shell/window.py`
  - `pywebview` window creation and shell-level UI constants
- Create: `app_shell/main.py`
  - desktop-shell entrypoint wiring runtime + window + graceful shutdown
- Create: `tools/run_macos_app.py`
  - local developer launcher for the app shell without packaging
- Create: `packaging/pyinstaller/macos_app.spec`
  - PyInstaller macOS bundle definition
- Create: `tools/build_macos_app.sh`
  - repeatable local build script for the macOS `.app`
- Create: `tests/test_app_shell.py`
  - TDD coverage for embedded runtime and shell orchestration
- Modify after implementation: `00_System/Workflow Guide.md`
  - add how to run the packaged shell and local shell-debug launcher
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark the macOS app shell as delivered once verified
- Modify after implementation: `docs/2026-04-11-macos-app-shell-design-spec.md`
  - update status from approved design to delivered behavior

This structure keeps packaging concerns separate from the Workbench product code. `workbench/` remains the app content. `app_shell/` becomes the lightweight desktop wrapper.

## Task 1: Add Red Tests For The Embedded Server Lifecycle

**Files:**
- Create: `tests/test_app_shell.py`

- [ ] **Step 1: Write failing tests for startup, readiness, and shutdown**

Create `tests/test_app_shell.py` starting with:

```python
import tempfile
import time
import unittest
from pathlib import Path

import httpx

from app_shell.runtime import EmbeddedWorkbenchServer


def seed_vault(root: Path) -> None:
    (root / "10_Domains/ai-application").mkdir(parents=True, exist_ok=True)
    (root / "10_Domains/ai-application/index.md").write_text(
        "---\nprimary_domain: ai-application\n---\n\n# AI Application\n",
        encoding="utf-8",
    )
    (root / "30_Wiki/ai-application").mkdir(parents=True, exist_ok=True)
    (root / "30_Wiki/ai-application/library-systems--synthesis.md").write_text(
        "---\n"
        "title: Library Systems\n"
        "note_type: synthesis\n"
        "primary_domain: ai-application\n"
        "source_refs: [\"raw/library\"]\n"
        "---\n\n"
        "# Library Systems\n\n"
        "## Source Summary\n"
        "Library systems support grounded answers.\n",
        encoding="utf-8",
    )


class AppShellRuntimeTests(unittest.TestCase):
    def test_embedded_server_starts_and_serves_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            server = EmbeddedWorkbenchServer(vault_root=root, config_path=root / "workbench.json")

            server.start()
            try:
                response = httpx.get(server.base_url, timeout=2.0)
                self.assertEqual(response.status_code, 200)
                self.assertIn("知識工作台", response.text)
            finally:
                server.stop()

    def test_embedded_server_exposes_health_and_stops_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            server = EmbeddedWorkbenchServer(vault_root=root, config_path=root / "workbench.json")

            server.start()
            base_url = server.base_url
            response = httpx.get(f"{base_url}/api/system/health", timeout=2.0)
            self.assertEqual(response.status_code, 200)

            server.stop()

            with self.assertRaises(Exception):
                httpx.get(base_url, timeout=0.5)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_app_shell -v
```

Expected:

- FAIL because `app_shell.runtime` and `EmbeddedWorkbenchServer` do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_app_shell.py
git commit -m "test: add macos app shell runtime coverage"
```

## Task 2: Implement The Embedded Workbench Runtime

**Files:**
- Create: `app_shell/__init__.py`
- Create: `app_shell/runtime.py`
- Modify: `requirements.txt`
- Test: `tests/test_app_shell.py`

- [ ] **Step 1: Add the desktop runtime dependency**

Append to `requirements.txt`:

```txt
pywebview>=5.1,<6
```

Do not add `PyInstaller` to `requirements.txt`; keep it as a packaging/build tool in the build script instead of a normal runtime dependency.

- [ ] **Step 2: Create the shell package marker**

Create `app_shell/__init__.py` with:

```python
"""Desktop app shell for Infinite Lore."""
```

- [ ] **Step 3: Implement `EmbeddedWorkbenchServer`**

Create `app_shell/runtime.py` with:

```python
from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Optional

import httpx
import uvicorn

from workbench.server import create_app


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class EmbeddedWorkbenchServer:
    def __init__(self, vault_root: Path, config_path: Path, host: str = "127.0.0.1", port: Optional[int] = None) -> None:
        self.vault_root = Path(vault_root).resolve()
        self.config_path = Path(config_path).resolve()
        self.host = host
        self.port = port or _pick_free_port()
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self, timeout: float = 10.0) -> None:
        app = create_app(vault_root=self.vault_root, config_path=self.config_path)
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        self.wait_until_ready(timeout=timeout)

    def wait_until_ready(self, timeout: float = 10.0) -> None:
        deadline = time.time() + timeout
        last_error: Optional[Exception] = None
        while time.time() < deadline:
            try:
                response = httpx.get(f"{self.base_url}/api/system/health", timeout=0.5)
                if response.status_code == 200:
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(0.1)
        raise RuntimeError(f"Embedded Workbench server did not become ready in time: {last_error}")

    def stop(self, timeout: float = 5.0) -> None:
        if not self._server:
            return
        self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=timeout)
        self._server = None
        self._thread = None
```

- [ ] **Step 4: Run the runtime tests**

Run:

```bash
python3 -m unittest tests.test_app_shell -v
```

Expected:

- PASS for the runtime lifecycle tests

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app_shell/__init__.py app_shell/runtime.py tests/test_app_shell.py
git commit -m "feat: add embedded app shell runtime"
```

## Task 3: Add Red Tests For Desktop Shell Orchestration

**Files:**
- Modify: `tests/test_app_shell.py`

- [ ] **Step 1: Add failing tests for window wiring and startup error handling**

Append to `tests/test_app_shell.py`:

```python
from unittest import mock

from app_shell.main import launch_app


class AppShellLaunchTests(unittest.TestCase):
    def test_launch_app_starts_server_then_opens_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)

            with mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls, mock.patch(
                "app_shell.main.open_main_window"
            ) as open_window:
                server = server_cls.return_value
                server.base_url = "http://127.0.0.1:9999"

                launch_app(vault_root=root, config_path=root / "workbench.json")

                server.start.assert_called_once()
                open_window.assert_called_once_with("http://127.0.0.1:9999")

    def test_launch_app_surfaces_startup_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)

            with mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls, mock.patch(
                "app_shell.main.open_error_dialog"
            ) as open_error:
                server = server_cls.return_value
                server.start.side_effect = RuntimeError("boot failed")

                with self.assertRaises(RuntimeError):
                    launch_app(vault_root=root, config_path=root / "workbench.json")

                open_error.assert_called_once()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_app_shell.AppShellLaunchTests -v
```

Expected:

- FAIL because `app_shell.main` does not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_app_shell.py
git commit -m "test: add macos app shell launch coverage"
```

## Task 4: Implement The pywebview Shell Entrypoint

**Files:**
- Create: `app_shell/window.py`
- Create: `app_shell/main.py`
- Create: `tools/run_macos_app.py`
- Test: `tests/test_app_shell.py`

- [ ] **Step 1: Create the webview window wrapper**

Create `app_shell/window.py` with:

```python
from __future__ import annotations

import webview


WINDOW_TITLE = "Infinite Lore"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 980


def open_main_window(url: str) -> None:
    window = webview.create_window(
        WINDOW_TITLE,
        url=url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(1200, 820),
        text_select=True,
    )
    webview.start(gui="cocoa", debug=False)


def open_error_dialog(message: str) -> None:
    raise RuntimeError(message)
```

Keep the first version minimal. No menu customizations, no multiple windows.

- [ ] **Step 2: Create the desktop app entrypoint**

Create `app_shell/main.py` with:

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app_shell.runtime import EmbeddedWorkbenchServer
from app_shell.window import open_error_dialog, open_main_window


def launch_app(vault_root: Path, config_path: Path) -> None:
    server = EmbeddedWorkbenchServer(vault_root=vault_root, config_path=config_path)
    try:
        server.start()
        open_main_window(server.base_url)
    except Exception as exc:
        open_error_dialog(str(exc))
        raise
    finally:
        server.stop()


def default_vault_root() -> Path:
    return Path.cwd().resolve()


def default_config_path() -> Path:
    return Path.home() / ".config" / "infinite_lore" / "workbench.json"
```

- [ ] **Step 3: Add a local desktop-shell launcher**

Create `tools/run_macos_app.py` with:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_shell.main import default_config_path, default_vault_root, launch_app


if __name__ == "__main__":
    launch_app(vault_root=default_vault_root(), config_path=default_config_path())
```

- [ ] **Step 4: Run the shell tests**

Run:

```bash
python3 -m unittest tests.test_app_shell -v
```

Expected:

- PASS for launch orchestration and runtime lifecycle tests

- [ ] **Step 5: Commit**

```bash
git add app_shell/window.py app_shell/main.py tools/run_macos_app.py tests/test_app_shell.py
git commit -m "feat: add macos app shell launcher"
```

## Task 5: Add Packaging Files For The macOS `.app`

**Files:**
- Create: `packaging/pyinstaller/macos_app.spec`
- Create: `tools/build_macos_app.sh`

- [ ] **Step 1: Create the PyInstaller spec**

Create `packaging/pyinstaller/macos_app.spec` with:

```python
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path.cwd()

datas = [
    (str(ROOT / "workbench" / "static"), "workbench/static"),
]

a = Analysis(
    ["tools/run_macos_app.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.lifespan.on"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Infinite Lore",
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Infinite Lore",
)
app = BUNDLE(
    coll,
    name="Infinite Lore.app",
    icon=None,
    bundle_identifier="com.tonytien.infinite-lore",
)
```

- [ ] **Step 2: Create the build script**

Create `tools/build_macos_app.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m PyInstaller --noconfirm packaging/pyinstaller/macos_app.spec
echo "Built: $ROOT/dist/Infinite Lore.app"
```

- [ ] **Step 3: Make the build script executable and verify file presence**

Run:

```bash
chmod +x tools/build_macos_app.sh
rg --files app_shell packaging tools tests | sed -n '1,120p'
```

Expected:

- output includes `tools/build_macos_app.sh`
- output includes `packaging/pyinstaller/macos_app.spec`

- [ ] **Step 4: Commit**

```bash
git add packaging/pyinstaller/macos_app.spec tools/build_macos_app.sh
git commit -m "build: add macos app shell packaging scaffold"
```

## Task 6: Verify Local Shell Launch And Packaging Flow

**Files:**
- Verify runtime files and packaging scaffold

- [ ] **Step 1: Run the local desktop shell entrypoint**

Run:

```bash
python3 tools/run_macos_app.py
```

Check manually:

- a single desktop-style app window opens
- `首頁` loads directly
- no browser tab is required

- [ ] **Step 2: Build the macOS `.app` bundle**

Run:

```bash
python3 -m PyInstaller --version
tools/build_macos_app.sh
```

Expected:

- `PyInstaller` version prints successfully
- build output includes `dist/Infinite Lore.app`

- [ ] **Step 3: Launch the built app bundle**

Run:

```bash
open "dist/Infinite Lore.app"
```

Check manually:

- app launches without Terminal
- main window opens
- Workbench loads

- [ ] **Step 4: Smoke-test the core flows in the app shell**

Check manually inside the packaged app:

- `首頁` ask works
- `收件匣` opens
- `知識庫` opens
- app close does not leave the embedded server running

- [ ] **Step 5: Commit any final build-scaffold adjustments**

```bash
git add requirements.txt app_shell tools packaging tests
git commit -m "feat: verify macos app shell local packaging flow"
```

## Task 7: Sync Docs And Final Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-11-macos-app-shell-design-spec.md`

- [ ] **Step 1: Update the workflow guide**

Add a `macOS App Shell` section describing:

- local shell debug launcher: `python3 tools/run_macos_app.py`
- local bundle build: `tools/build_macos_app.sh`
- first-version scope: single main window, hidden localhost, same vault flow

- [ ] **Step 2: Update the roadmap**

Mark the macOS app shell as delivered only if Task 6 verification truly passed.

- [ ] **Step 3: Update the design spec status**

Change:

```md
**Status:** Draft v1 awaiting user review
```

to:

```md
**Status:** Delivered v1
```

only after the packaged shell is verified.

- [ ] **Step 4: Run full verification**

Run:

```bash
python3 -m unittest tests.test_app_shell tests.test_workbench_api tests.test_query_ask tests.test_reflection_feedback tests.test_automation_scan tests.test_relation_index tests.test_import_bundle tests.test_wiki_compile tests.test_multimodal_detect tests.test_image_adapter tests.test_vision_ocr tests.test_health_check -v
python3 tools/health_check.py .
```

Also run:

```bash
git diff --check
git status --short --branch
```

Expected:

- tests pass
- health check passes
- diff formatting is clean
- branch status is explicitly reportable

- [ ] **Step 5: Commit**

```bash
git add 00_System/Workflow\ Guide.md docs/2026-04-08-execution-roadmap.md docs/2026-04-11-macos-app-shell-design-spec.md
git commit -m "docs: sync macos app shell delivery"
```

## Self-Review

Spec coverage check:

- single main window: covered by Tasks 3, 4, and 6
- hidden localhost and managed runtime: covered by Tasks 1, 2, 4, and 6
- existing vault/config compatibility: covered by Tasks 2 and 4
- packaging as `.app`: covered by Tasks 5 and 6
- out-of-scope native extras remain excluded: respected by file structure and task boundaries
- docs/code alignment: covered by Task 7

Placeholder scan:

- no placeholder markers remain in task steps
- every code-changing step contains concrete file paths, commands, and code

Type consistency:

- `EmbeddedWorkbenchServer` is defined once and reused consistently
- `launch_app()`, `open_main_window()`, and `open_error_dialog()` names stay consistent across tests and implementation

Execution handoff:

This plan is ready for `superpowers:subagent-driven-development`.
