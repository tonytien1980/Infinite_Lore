from __future__ import annotations

from pathlib import Path
from typing import Optional

WINDOW_TITLE = "Infinite Lore"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 980

try:
    import webview
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    webview = None


def prompt_for_vault_root(parent_window: Optional[object]) -> Optional[Path]:
    if parent_window is None or webview is None:
        return None

    selected = parent_window.create_file_dialog(webview.FOLDER_DIALOG, directory=str(Path.home()))
    if not selected:
        return None
    return Path(selected[0]).expanduser().resolve()


def open_main_window(url: str) -> None:
    if webview is None:
        raise RuntimeError("pywebview is not installed")

    webview.create_window(
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
