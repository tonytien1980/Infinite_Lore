# macOS App Shell Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the shipped macOS desktop shell less layout-dependent, clearer during launch and failure states, and more stable as a real everyday app surface before release hardening.

**Architecture:** Keep the existing FastAPI Workbench and embedded `uvicorn` runtime. Add a small shell-state layer for remembered vault selection, then promote the shell window from a passive browser wrapper into a lightweight controller surface that can show Traditional Chinese loading and error states before the Workbench is ready. Keep the final desktop architecture local-first and single-window.

**Tech Stack:** Python 3.9, `unittest`, `httpx`, `pywebview`, `uvicorn`, FastAPI, PyInstaller, existing Workbench static frontend

---

## File Structure

- Create: `app_shell/state.py`
  - persist shell-only state such as the last confirmed vault root
- Modify: `app_shell/main.py`
  - resolve the launch vault in a safer order, drive the shell controller, and stop relying on one fragile app path
- Modify: `app_shell/window.py`
  - create the startup shell window, Traditional Chinese loading / error HTML, folder picker wrapper, and shell bridge callbacks
- Modify: `tools/run_macos_app.py`
  - launch the new shell controller entrypoint instead of the old direct vault bootstrap
- Create: `packaging/macos/requirements-shell.txt`
  - pin the validated local macOS shell dependency set used for build and debug verification
- Modify: `tools/build_macos_app.sh`
  - fail fast with a clear setup message if the shell build dependencies are missing
- Modify: `tests/test_app_shell.py`
  - cover saved-vault fallback, folder-picker fallback, Traditional Chinese loading / error states, and controller behavior
- Modify after implementation: `00_System/Workflow Guide.md`
  - explain how the shell now resolves the vault, how the fallback picker works, and how to build / run it
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark the polish phase as delivered and move the next recommended step to distribution hardening
- Modify after implementation: `docs/2026-04-11-macos-app-shell-design-spec.md`
  - update the design spec status from approved to delivered
- Modify after implementation: `docs/2026-04-11-macos-app-shell-polish-spec.md`
  - update the polish spec status from approved to delivered

This split keeps the shell concerns local to `app_shell/` and avoids dragging Workbench product code into desktop-only behavior.

## Task 1: Add Red Tests For Safer Vault Resolution

**Files:**
- Modify: `tests/test_app_shell.py`

- [ ] **Step 1: Add failing tests for saved vault reuse and picker fallback**

Append these imports near the top of `tests/test_app_shell.py`:

```python
import json

from app_shell.main import default_vault_root, resolve_launch_vault_root
from app_shell.state import default_shell_state_path
```

Append these tests to `AppShellLaunchTests`:

```python
    def test_resolve_launch_vault_root_uses_saved_state_when_auto_candidates_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            saved_vault = temp_root / "Saved Vault"
            saved_vault.mkdir(parents=True)
            seed_vault(saved_vault)

            config_path = temp_root / "config" / "workbench.json"
            state_path = default_shell_state_path(config_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"last_vault_root": str(saved_vault.resolve())}),
                encoding="utf-8",
            )

            invalid_cwd = temp_root / "not-a-vault"
            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=invalid_cwd,
            ):
                resolved = resolve_launch_vault_root(config_path=config_path, prompt_parent=None)

            self.assertEqual(resolved, saved_vault.resolve())

    def test_resolve_launch_vault_root_prompts_and_saves_valid_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            selected_vault = temp_root / "Chosen Vault"
            selected_vault.mkdir(parents=True)
            seed_vault(selected_vault)

            config_path = temp_root / "config" / "workbench.json"
            state_path = default_shell_state_path(config_path)

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=temp_root / "not-a-vault",
            ), mock.patch(
                "app_shell.main.prompt_for_vault_root",
                return_value=selected_vault,
            ):
                resolved = resolve_launch_vault_root(config_path=config_path, prompt_parent=mock.Mock())

            self.assertEqual(resolved, selected_vault.resolve())
            saved_payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_payload["last_vault_root"], str(selected_vault.resolve()))

    def test_resolve_launch_vault_root_raises_product_error_when_picker_is_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            config_path = temp_root / "config" / "workbench.json"

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=temp_root / "not-a-vault",
            ), mock.patch(
                "app_shell.main.prompt_for_vault_root",
                return_value=None,
            ):
                with self.assertRaisesRegex(RuntimeError, "找不到可用的知識庫資料夾"):
                    resolve_launch_vault_root(config_path=config_path, prompt_parent=mock.Mock())
```

- [ ] **Step 2: Run the new tests and confirm they fail**

Run:

```bash
python3 -m unittest \
  tests.test_app_shell.AppShellLaunchTests.test_resolve_launch_vault_root_uses_saved_state_when_auto_candidates_fail \
  tests.test_app_shell.AppShellLaunchTests.test_resolve_launch_vault_root_prompts_and_saves_valid_selection \
  tests.test_app_shell.AppShellLaunchTests.test_resolve_launch_vault_root_raises_product_error_when_picker_is_cancelled \
  -v
```

Expected:

- FAIL because `app_shell.state` and `resolve_launch_vault_root` do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_app_shell.py
git commit -m "test: cover macos app shell vault fallback"
```

## Task 2: Implement Remembered Vault Resolution And Fallback Picker Support

**Files:**
- Create: `app_shell/state.py`
- Modify: `app_shell/main.py`
- Modify: `tests/test_app_shell.py`

- [ ] **Step 1: Create shell-state helpers**

Create `app_shell/state.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

STATE_FILE_NAME = "app-shell.json"


def default_shell_state_path(config_path: Path) -> Path:
    return Path(config_path).expanduser().resolve().with_name(STATE_FILE_NAME)


def load_saved_vault_root(state_path: Path) -> Optional[Path]:
    if not state_path.exists():
        return None

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None

    raw_value = payload.get("last_vault_root")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    return Path(raw_value).expanduser().resolve()


def save_saved_vault_root(state_path: Path, vault_root: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_vault_root": str(Path(vault_root).expanduser().resolve())}
    state_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
```

- [ ] **Step 2: Add vault validation and fallback resolution to `app_shell/main.py`**

Update `app_shell/main.py` so the top-level functions look like this:

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from app_shell.runtime import EmbeddedWorkbenchServer
from app_shell.state import default_shell_state_path, load_saved_vault_root, save_saved_vault_root
from app_shell.window import open_error_dialog, open_main_window, prompt_for_vault_root

_VAULT_MARKERS = ("10_Domains", "30_Wiki")


def is_valid_vault_root(candidate: Path) -> bool:
    candidate = Path(candidate).expanduser().resolve()
    return candidate.exists() and all((candidate / marker).exists() for marker in _VAULT_MARKERS)


def resolve_launch_vault_root(config_path: Path, prompt_parent: object | None) -> Path:
    state_path = default_shell_state_path(config_path)
    candidates = []

    if getattr(sys, "frozen", False):
        frozen_root = _default_vault_root_from_frozen_executable(Path(sys.executable))
        if frozen_root is not None:
            candidates.append(frozen_root)

    candidates.append(Path.cwd().resolve())

    saved_root = load_saved_vault_root(state_path)
    if saved_root is not None:
        candidates.append(saved_root)

    for candidate in candidates:
        if is_valid_vault_root(candidate):
            return candidate.resolve()

    selected_root = prompt_for_vault_root(prompt_parent)
    if selected_root is None:
        raise RuntimeError("找不到可用的知識庫資料夾，且你尚未選擇資料夾。")
    if not is_valid_vault_root(selected_root):
        raise RuntimeError("你選擇的資料夾不是有效的 Infinite Lore 知識庫。")

    save_saved_vault_root(state_path, selected_root)
    return selected_root.resolve()


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


def default_vault_root(config_path: Path | None = None) -> Path:
    if config_path is None:
        config_path = default_config_path()
    return resolve_launch_vault_root(config_path=config_path, prompt_parent=None)
```

Keep `_default_vault_root_from_frozen_executable` and `default_config_path()` in the file, but let `default_vault_root()` delegate to the new resolver so source-launch and packaged-launch behavior stay aligned.

- [ ] **Step 3: Run the Task 1 tests again**

Run:

```bash
python3 -m unittest \
  tests.test_app_shell.AppShellLaunchTests.test_resolve_launch_vault_root_uses_saved_state_when_auto_candidates_fail \
  tests.test_app_shell.AppShellLaunchTests.test_resolve_launch_vault_root_prompts_and_saves_valid_selection \
  tests.test_app_shell.AppShellLaunchTests.test_resolve_launch_vault_root_raises_product_error_when_picker_is_cancelled \
  -v
```

Expected:

- PASS for all three tests

- [ ] **Step 4: Commit**

```bash
git add app_shell/state.py app_shell/main.py tests/test_app_shell.py
git commit -m "feat: harden macos app shell vault resolution"
```

## Task 3: Add Red Tests For Loading And Error States

**Files:**
- Modify: `tests/test_app_shell.py`

- [ ] **Step 1: Add failing tests for Traditional Chinese loading and error surfaces**

Append these imports near the top of `tests/test_app_shell.py`:

```python
from app_shell.main import AppShellController
from app_shell.window import build_error_html, build_loading_html
```

Append these tests:

```python
class AppShellUiTests(unittest.TestCase):
    def test_build_loading_html_uses_traditional_chinese_copy(self) -> None:
        html = build_loading_html("正在準備知識庫...")

        self.assertIn("Infinite Lore", html)
        self.assertIn("正在準備知識庫", html)
        self.assertNotIn("Loading", html)

    def test_build_error_html_includes_recovery_actions(self) -> None:
        html = build_error_html(
            title="無法開啟知識工作台",
            message="請重新選擇知識庫資料夾。",
            show_retry=True,
            show_choose_vault=True,
        )

        self.assertIn("重新嘗試", html)
        self.assertIn("選擇知識庫資料夾", html)
        self.assertIn("結束應用程式", html)
        self.assertIn("window.pywebview.api.retry_launch()", html)
        self.assertIn("window.pywebview.api.choose_vault()", html)

    def test_controller_loads_workbench_url_after_successful_boot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            controller = AppShellController(config_path=root / "workbench.json")
            controller.window = mock.Mock()

            with mock.patch(
                "app_shell.main.resolve_launch_vault_root",
                return_value=root.resolve(),
            ), mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls:
                server = server_cls.return_value
                server.base_url = "http://127.0.0.1:7788"

                controller.bootstrap(controller.window)

            controller.window.load_url.assert_called_once_with("http://127.0.0.1:7788")

    def test_controller_renders_error_html_when_boot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            controller = AppShellController(config_path=root / "workbench.json")
            controller.window = mock.Mock()

            with mock.patch(
                "app_shell.main.resolve_launch_vault_root",
                side_effect=RuntimeError("找不到可用的知識庫資料夾。"),
            ):
                controller.bootstrap(controller.window)

            controller.window.load_html.assert_called()
            rendered_html = controller.window.load_html.call_args[0][0]
            self.assertIn("找不到可用的知識庫資料夾", rendered_html)
```

- [ ] **Step 2: Run the UI tests and confirm they fail**

Run:

```bash
python3 -m unittest tests.test_app_shell.AppShellUiTests -v
```

Expected:

- FAIL because `AppShellController`, `build_loading_html`, and `build_error_html` do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add tests/test_app_shell.py
git commit -m "test: cover macos app shell loading states"
```

## Task 4: Implement The Shell Controller, Loading View, And Error View

**Files:**
- Modify: `app_shell/main.py`
- Modify: `app_shell/window.py`
- Modify: `tools/run_macos_app.py`
- Modify: `tests/test_app_shell.py`

- [ ] **Step 1: Extend `app_shell/window.py` with loading / error helpers**

Replace the simple `window.py` helpers with:

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional

WINDOW_TITLE = "Infinite Lore"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 980
WINDOW_MIN_SIZE = (1240, 840)
WINDOW_BACKGROUND = "#0f172a"
SHELL_LOCALIZATION = {
    "global.quit": "結束",
    "cocoa.menu.about": "關於 Infinite Lore",
}

try:
    import webview
except ModuleNotFoundError:  # pragma: no cover
    webview = None


def build_loading_html(message: str) -> str:
    return f"""<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="utf-8" />
    <title>Infinite Lore</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: radial-gradient(circle at top, #1e293b, #0f172a 60%);
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
      }}
      .shell-card {{
        width: min(520px, calc(100vw - 64px));
        padding: 28px 32px;
        border-radius: 20px;
        background: rgba(15, 23, 42, 0.82);
        box-shadow: 0 18px 60px rgba(15, 23, 42, 0.32);
      }}
      .label {{ opacity: 0.75; font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }}
      h1 {{ margin: 10px 0 12px; font-size: 32px; }}
      p {{ margin: 0; font-size: 16px; line-height: 1.7; }}
    </style>
  </head>
  <body>
    <main class="shell-card">
      <div class="label">知識工作台</div>
      <h1>Infinite Lore</h1>
      <p>{message}</p>
    </main>
  </body>
</html>"""


def build_error_html(title: str, message: str, show_retry: bool, show_choose_vault: bool) -> str:
    retry_button = (
        '<button onclick="window.pywebview.api.retry_launch()">重新嘗試</button>'
        if show_retry
        else ""
    )
    choose_button = (
        '<button onclick="window.pywebview.api.choose_vault()">選擇知識庫資料夾</button>'
        if show_choose_vault
        else ""
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="utf-8" />
    <title>Infinite Lore</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: linear-gradient(180deg, #fff7ed 0%, #fffbeb 100%);
        color: #7c2d12;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
      }}
      .shell-card {{
        width: min(580px, calc(100vw - 64px));
        padding: 28px 32px;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 20px 50px rgba(194, 65, 12, 0.12);
      }}
      .actions {{
        display: flex;
        gap: 12px;
        margin-top: 20px;
        flex-wrap: wrap;
      }}
      button {{
        border: 0;
        border-radius: 999px;
        padding: 10px 16px;
        font: inherit;
        cursor: pointer;
      }}
    </style>
  </head>
  <body>
    <main class="shell-card">
      <h1>{title}</h1>
      <p>{message}</p>
      <div class="actions">
        {retry_button}
        {choose_button}
        <button onclick="window.pywebview.api.quit_app()">結束應用程式</button>
      </div>
    </main>
  </body>
</html>"""


class ShellWindowApi:
    def __init__(self, controller: object) -> None:
        self.controller = controller

    def retry_launch(self) -> None:
        self.controller.retry_launch()

    def choose_vault(self) -> None:
        self.controller.choose_vault()

    def quit_app(self) -> None:
        self.controller.quit_app()


def create_shell_window(api: ShellWindowApi):
    if webview is None:
        raise RuntimeError("pywebview is not installed")
    return webview.create_window(
        WINDOW_TITLE,
        html=build_loading_html("正在啟動 Infinite Lore..."),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=WINDOW_MIN_SIZE,
        background_color=WINDOW_BACKGROUND,
        text_select=True,
    )


def start_shell_window(window, bootstrap) -> None:
    if webview is None:
        raise RuntimeError("pywebview is not installed")
    webview.start(
        bootstrap,
        args=(window,),
        gui="cocoa",
        debug=False,
        private_mode=True,
        localization=SHELL_LOCALIZATION,
    )


def prompt_for_vault_root(parent_window) -> Optional[Path]:
    if parent_window is None or webview is None:
        return None
    selected = parent_window.create_file_dialog(webview.FOLDER_DIALOG, directory=str(Path.home()))
    if not selected:
        return None
    return Path(selected[0]).expanduser().resolve()


def open_error_dialog(message: str) -> None:
    raise RuntimeError(message)
```

- [ ] **Step 2: Add the controller to `app_shell/main.py`**

Update `app_shell/main.py` so the main orchestration looks like this:

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from app_shell.runtime import EmbeddedWorkbenchServer
from app_shell.state import default_shell_state_path, load_saved_vault_root, save_saved_vault_root
from app_shell.window import (
    ShellWindowApi,
    build_error_html,
    build_loading_html,
    create_shell_window,
    open_error_dialog,
    prompt_for_vault_root,
    start_shell_window,
)

_VAULT_MARKERS = ("10_Domains", "30_Wiki")


class AppShellController:
    def __init__(self, config_path: Path, initial_vault_root: Path | None = None) -> None:
        self.config_path = Path(config_path).expanduser().resolve()
        self.initial_vault_root = initial_vault_root.resolve() if initial_vault_root else None
        self.window = None
        self.server: EmbeddedWorkbenchServer | None = None

    def run(self) -> None:
        api = ShellWindowApi(self)
        window = create_shell_window(api)
        start_shell_window(window, self.bootstrap)

    def bootstrap(self, window) -> None:
        self.window = window
        self._attempt_launch(allow_prompt=self.initial_vault_root is None)

    def retry_launch(self) -> None:
        self._attempt_launch(allow_prompt=False)

    def choose_vault(self) -> None:
        if self.window is None:
            return
        selected_root = prompt_for_vault_root(self.window)
        if selected_root is None:
            self._render_error("無法開啟知識工作台", "你尚未選擇知識庫資料夾。")
            return
        if not is_valid_vault_root(selected_root):
            self._render_error("無法開啟知識工作台", "你選擇的資料夾不是有效的 Infinite Lore 知識庫。")
            return

        save_saved_vault_root(default_shell_state_path(self.config_path), selected_root)
        self.initial_vault_root = selected_root.resolve()
        self._attempt_launch(allow_prompt=False)

    def quit_app(self) -> None:
        if self.server is not None:
            self.server.stop()
            self.server = None
        if self.window is not None:
            self.window.destroy()

    def _attempt_launch(self, allow_prompt: bool) -> None:
        if self.window is None:
            raise RuntimeError("Shell window is not ready")

        self.window.load_html(build_loading_html("正在準備知識庫與本機服務..."))
        try:
            vault_root = self.initial_vault_root or resolve_launch_vault_root(
                config_path=self.config_path,
                prompt_parent=self.window if allow_prompt else None,
            )
            self.server = EmbeddedWorkbenchServer(vault_root=vault_root, config_path=self.config_path)
            self.server.start()
            self.window.load_url(self.server.base_url)
        except Exception as exc:
            self._render_error("無法開啟知識工作台", str(exc))

    def _render_error(self, title: str, message: str) -> None:
        if self.window is None:
            open_error_dialog(message)
            return
        self.window.load_html(
            build_error_html(
                title=title,
                message=message,
                show_retry=True,
                show_choose_vault=True,
            )
        )


def launch_app(vault_root: Path | None = None, config_path: Path | None = None) -> None:
    config_path = Path(config_path or default_config_path()).expanduser().resolve()
    controller = AppShellController(config_path=config_path, initial_vault_root=vault_root)
    controller.run()
```

Keep `open_error_dialog` only as a last-resort fallback when the window does not exist yet.

- [ ] **Step 3: Update the source launcher**

Replace `tools/run_macos_app.py` with:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_shell.main import default_config_path, launch_app


if __name__ == "__main__":
    launch_app(config_path=default_config_path())
```

- [ ] **Step 4: Run the UI tests again**

Run:

```bash
python3 -m unittest tests.test_app_shell.AppShellUiTests -v
```

Expected:

- PASS for loading HTML, error HTML, and controller behavior

- [ ] **Step 5: Commit**

```bash
git add app_shell/main.py app_shell/window.py tools/run_macos_app.py tests/test_app_shell.py
git commit -m "feat: polish macos app shell startup flow"
```

## Task 5: Pin The Verified macOS Shell Build Baseline

**Files:**
- Create: `packaging/macos/requirements-shell.txt`
- Modify: `tools/build_macos_app.sh`

- [ ] **Step 1: Create the macOS shell dependency baseline**

Create `packaging/macos/requirements-shell.txt` with:

```txt
pywebview==5.4
PyInstaller==6.19.0
pyobjc-core==11.1
pyobjc-framework-Cocoa==11.1
pyobjc-framework-Quartz==11.1
pyobjc-framework-WebKit==11.1
pyobjc-framework-Security==11.1
```

- [ ] **Step 2: Fail fast when build dependencies are missing**

Update `tools/build_macos_app.sh` to:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import importlib
missing = []
for module_name in ("webview", "PyInstaller"):
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        missing.append(module_name)
if missing:
    print(
        "缺少 macOS app shell 打包依賴。請先執行："
        " python3 -m pip install -r packaging/macos/requirements-shell.txt",
        flush=True,
    )
    raise SystemExit(1)
PY

python3 -m PyInstaller --noconfirm packaging/pyinstaller/macos_app.spec
echo "Built: $ROOT/dist/Infinite Lore.app"
```

- [ ] **Step 3: Run the build script smoke check**

Run:

```bash
tools/build_macos_app.sh
```

Expected:

- If dependencies are present, the build succeeds and prints `Built: .../dist/Infinite Lore.app`
- If dependencies are missing, the script fails early with the new Traditional Chinese setup message

- [ ] **Step 4: Commit**

```bash
git add packaging/macos/requirements-shell.txt tools/build_macos_app.sh
git commit -m "build: pin macos app shell baseline"
```

## Task 6: Sync Docs And Run Full Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-11-macos-app-shell-design-spec.md`
- Modify: `docs/2026-04-11-macos-app-shell-polish-spec.md`

- [ ] **Step 1: Update the operator docs**

Update `00_System/Workflow Guide.md` to say:

```md
### macOS App Shell

- source launch: `python3 tools/run_macos_app.py`
- packaged build: `tools/build_macos_app.sh`
- first fallback when the app cannot auto-resolve the vault:
  - it opens a `選擇知識庫資料夾` picker
  - it remembers the confirmed vault for the next launch
- if launch still fails, the shell shows a Traditional Chinese recovery view instead of a raw traceback
```

Update `docs/2026-04-11-macos-app-shell-design-spec.md` status to:

```md
**Status:** Delivered and verified locally
```

Update `docs/2026-04-11-macos-app-shell-polish-spec.md` status to:

```md
**Status:** Delivered and verified locally
```

Update the macOS shell section in `docs/2026-04-08-execution-roadmap.md` so it records:

```md
### 4.13 macOS App Shell Polish

Completed:

- desktop shell no longer depends only on `<vault>/dist/Infinite Lore.app`
- remembered vault selection supports launches outside the repo tree
- startup and failure states are surfaced in Traditional Chinese shell views
- shell build guidance now uses a pinned macOS dependency baseline
```

- [ ] **Step 2: Run the regression and shell verification commands**

Run:

```bash
python3 -m unittest tests.test_app_shell -v
python3 tools/health_check.py .
node --check workbench/static/app.js
tools/build_macos_app.sh
```

Expected:

- `tests.test_app_shell` passes
- vault health check passes
- `app.js` syntax check passes
- macOS app bundle builds successfully

- [ ] **Step 3: Run live shell verification**

Run:

```bash
python3 tools/run_macos_app.py
```

Verify manually:

- the shell first shows a Traditional Chinese loading state
- if the current path is not a valid vault, the app can prompt for `選擇知識庫資料夾`
- after choosing a valid vault, the Workbench homepage loads

Then verify the packaged app outside the repo build path:

```bash
rm -rf "/tmp/Infinite Lore.app"
cp -R "dist/Infinite Lore.app" "/tmp/Infinite Lore.app"
open "/tmp/Infinite Lore.app"
```

Verify manually:

- the copied app outside the repo tree can still launch
- the picker fallback works when automatic resolution cannot infer the vault
- quitting and reopening the copied app reuses the remembered vault without prompting again

- [ ] **Step 4: Commit the docs sync**

```bash
git add \
  00_System/Workflow\ Guide.md \
  docs/2026-04-08-execution-roadmap.md \
  docs/2026-04-11-macos-app-shell-design-spec.md \
  docs/2026-04-11-macos-app-shell-polish-spec.md
git commit -m "docs: sync macos app shell polish delivery"
```

