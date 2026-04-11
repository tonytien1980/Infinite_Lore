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
    prompt_for_vault_root,
    start_shell_window,
)

_VAULT_MARKERS = ("10_Domains", "30_Wiki")


def is_valid_vault_root(candidate: Path) -> bool:
    candidate = Path(candidate).expanduser().resolve()
    return candidate.exists() and all((candidate / marker).exists() for marker in _VAULT_MARKERS)

def resolve_launch_vault_root(config_path: Path, prompt_parent: Optional[object]) -> Path:
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


class AppShellController:
    def __init__(self, config_path: Path, initial_vault_root: Optional[Path] = None) -> None:
        self.config_path = Path(config_path)
        self.initial_vault_root = Path(initial_vault_root).resolve() if initial_vault_root is not None else None
        self.window: Optional[object] = None
        self.server: Optional[EmbeddedWorkbenchServer] = None

    def run(self) -> None:
        api = ShellWindowApi(self)
        shell_window = create_shell_window(api)
        self.window = shell_window
        start_shell_window(shell_window, self.bootstrap)

    def bootstrap(self, window: object) -> None:
        self.window = window
        window.load_html(build_loading_html("正在準備你的 Infinite Lore 工作台與知識庫..."))
        self._stop_server()

        try:
            vault_root = self._resolve_vault_root(prompt_parent=window)
            server = EmbeddedWorkbenchServer(vault_root=vault_root, config_path=self.config_path)
            self.server = server
            server.start()
            window.load_url(server.base_url)
        except Exception as exc:
            self._stop_server()
            self._render_error(str(exc))

    def retry_launch(self) -> None:
        if self.window is None:
            return
        self.bootstrap(self.window)

    def choose_vault(self) -> None:
        if self.window is None:
            return

        selected_root = prompt_for_vault_root(self.window)
        if selected_root is None:
            self._render_error("找不到可用的知識庫資料夾，且你尚未選擇資料夾。")
            return
        if not is_valid_vault_root(selected_root):
            self._render_error("你選擇的資料夾不是有效的 Infinite Lore 知識庫。")
            return

        selected_root = selected_root.resolve()
        save_saved_vault_root(default_shell_state_path(self.config_path), selected_root)
        self.initial_vault_root = selected_root
        self.retry_launch()

    def quit_app(self) -> None:
        self._stop_server()
        if self.window is not None and hasattr(self.window, "destroy"):
            self.window.destroy()

    def _resolve_vault_root(self, prompt_parent: object) -> Path:
        if self.initial_vault_root is not None:
            return self.initial_vault_root.resolve()

        return resolve_launch_vault_root(
            config_path=self.config_path,
            prompt_parent=prompt_parent,
        )

    def _render_error(self, message: str) -> None:
        if self.window is None:
            raise RuntimeError(message)

        self.window.load_html(
            build_error_html(
                title="無法開啟知識工作台",
                message=message,
                show_retry=True,
                show_choose_vault=True,
            )
        )

    def _stop_server(self) -> None:
        if self.server is None:
            return
        self.server.stop()
        self.server = None


def launch_app(vault_root: Optional[Path] = None, config_path: Optional[Path] = None) -> None:
    if config_path is None:
        config_path = default_config_path()

    controller = AppShellController(
        config_path=config_path,
        initial_vault_root=vault_root,
    )
    controller.run()


def default_vault_root(config_path: Optional[Path] = None, prompt_parent: Optional[object] = None) -> Path:
    if config_path is None:
        config_path = default_config_path()
    return resolve_launch_vault_root(config_path=config_path, prompt_parent=prompt_parent)


def _default_vault_root_from_frozen_executable(executable: Path) -> Optional[Path]:
    try:
        macos_dir = executable.parents[0]
        contents_dir = executable.parents[1]
        app_bundle = executable.parents[2]
        dist_dir = executable.parents[3]
        vault_root = executable.parents[4]
    except IndexError:
        return None

    if macos_dir.name != "MacOS":
        return None
    if contents_dir.name != "Contents":
        return None
    if app_bundle.suffix != ".app":
        return None
    if dist_dir.name != "dist":
        return None
    if not all((vault_root / marker).exists() for marker in _VAULT_MARKERS):
        return None
    return vault_root.resolve()


def default_config_path() -> Path:
    return Path.home() / ".config" / "infinite_lore" / "workbench.json"
