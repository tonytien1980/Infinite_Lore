from __future__ import annotations

from pathlib import Path

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
