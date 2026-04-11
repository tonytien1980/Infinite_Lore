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
