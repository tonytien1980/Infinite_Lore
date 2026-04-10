from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from app_shell.runtime import EmbeddedWorkbenchServer
from app_shell.window import open_error_dialog, open_main_window

_VAULT_MARKERS = ("10_Domains", "30_Wiki")


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
    if getattr(sys, "frozen", False):
        frozen_root = _default_vault_root_from_frozen_executable(Path(sys.executable))
        if frozen_root is not None:
            return frozen_root
    return Path.cwd().resolve()


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
