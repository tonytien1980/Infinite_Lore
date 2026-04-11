from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

WINDOW_TITLE = "Infinite Lore"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 980
WINDOW_MIN_SIZE = (1200, 820)
ERROR_WINDOW_WIDTH = 760
ERROR_WINDOW_HEIGHT = 560
ERROR_WINDOW_MIN_SIZE = (640, 420)

try:
    import webview
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    webview = None


def build_loading_html(startup_copy: str) -> str:
    safe_copy = escape(startup_copy)
    return f"""<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="utf-8" />
    <title>{WINDOW_TITLE}</title>
    <style>
      :root {{
        color-scheme: light dark;
        font-family: -apple-system, BlinkMacSystemFont, "PingFang TC", sans-serif;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: linear-gradient(180deg, #f5f1e8 0%, #ede6d8 100%);
        color: #1f1f1f;
      }}
      .panel {{
        width: min(560px, calc(100vw - 64px));
        padding: 40px 36px;
        border-radius: 24px;
        background: rgba(255, 255, 255, 0.9);
        box-shadow: 0 20px 48px rgba(68, 52, 27, 0.16);
      }}
      .eyebrow {{
        margin: 0 0 12px;
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #73563a;
      }}
      h1 {{
        margin: 0 0 12px;
        font-size: 34px;
      }}
      p {{
        margin: 0;
        font-size: 16px;
        line-height: 1.6;
      }}
    </style>
  </head>
  <body>
    <main class="panel">
      <p class="eyebrow">Infinite Lore</p>
      <h1>正在啟動知識工作台</h1>
      <p>{safe_copy}</p>
    </main>
  </body>
</html>
"""


def build_error_html(
    title: str,
    message: str,
    *,
    show_retry: bool,
    show_choose_vault: bool,
) -> str:
    safe_title = escape(title)
    safe_message = escape(message)
    actions = []
    if show_retry:
        actions.append(
            '<button type="button" class="primary" onclick="window.pywebview.api.retry_launch()">重新嘗試</button>'
        )
    if show_choose_vault:
        actions.append(
            '<button type="button" onclick="window.pywebview.api.choose_vault()">選擇知識庫資料夾</button>'
        )
    actions.append('<button type="button" class="ghost" onclick="window.pywebview.api.quit_app()">結束應用程式</button>')
    action_markup = "\n        ".join(actions)

    return f"""<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="utf-8" />
    <title>{WINDOW_TITLE}</title>
    <style>
      :root {{
        color-scheme: light dark;
        font-family: -apple-system, BlinkMacSystemFont, "PingFang TC", sans-serif;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: radial-gradient(circle at top, #f6eadf 0%, #efe5d8 42%, #e5d9c9 100%);
        color: #241c13;
      }}
      .panel {{
        width: min(620px, calc(100vw - 64px));
        padding: 40px 36px;
        border-radius: 24px;
        background: rgba(255, 250, 244, 0.96);
        box-shadow: 0 24px 54px rgba(57, 37, 15, 0.16);
      }}
      .label {{
        margin: 0 0 12px;
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #925b2a;
      }}
      h1 {{
        margin: 0 0 16px;
        font-size: 32px;
      }}
      p {{
        margin: 0;
        white-space: pre-wrap;
        font-size: 15px;
        line-height: 1.7;
      }}
      .actions {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 28px;
      }}
      button {{
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        font-size: 14px;
        cursor: pointer;
        background: #ead7c4;
        color: #2d2015;
      }}
      .primary {{
        background: #7b4f28;
        color: #fffaf5;
      }}
      .ghost {{
        background: #d9c4b2;
      }}
    </style>
  </head>
  <body>
    <main class="panel">
      <p class="label">Infinite Lore</p>
      <h1>{safe_title}</h1>
      <p>{safe_message}</p>
      <div class="actions">
        {action_markup}
      </div>
    </main>
  </body>
</html>
"""


class ShellWindowApi:
    def __init__(self, controller: object) -> None:
        self._controller = controller

    def retry_launch(self) -> None:
        self._controller.retry_launch()

    def choose_vault(self) -> None:
        self._controller.choose_vault()

    def quit_app(self) -> None:
        self._controller.quit_app()


def prompt_for_vault_root(parent_window: Optional[object]) -> Optional[Path]:
    if parent_window is None or webview is None:
        return None

    selected = parent_window.create_file_dialog(webview.FOLDER_DIALOG, directory=str(Path.home()))
    if not selected:
        return None
    return Path(selected[0]).expanduser().resolve()


def create_shell_window(api: Optional[object]) -> object:
    if webview is None:
        raise RuntimeError("pywebview is not installed")

    return webview.create_window(
        WINDOW_TITLE,
        html=build_loading_html("正在準備 Infinite Lore 工作台..."),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=WINDOW_MIN_SIZE,
        text_select=True,
    )


def start_shell_window(window: object, bootstrap_callback: object) -> None:
    if webview is None:
        raise RuntimeError("pywebview is not installed")

    webview.start(lambda: bootstrap_callback(window), gui="cocoa", debug=False)


def open_main_window(url: str) -> None:
    if webview is None:
        raise RuntimeError("pywebview is not installed")

    webview.create_window(
        WINDOW_TITLE,
        url=url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=WINDOW_MIN_SIZE,
        text_select=True,
    )
    webview.start(gui="cocoa", debug=False)


def open_error_dialog(message: str) -> None:
    if webview is None:
        raise RuntimeError(message)

    webview.create_window(
        WINDOW_TITLE,
        html=build_error_html(
            title="無法啟動 Infinite Lore",
            message=message,
            show_retry=False,
            show_choose_vault=False,
        ),
        width=ERROR_WINDOW_WIDTH,
        height=ERROR_WINDOW_HEIGHT,
        min_size=ERROR_WINDOW_MIN_SIZE,
        text_select=True,
    )
    webview.start(gui="cocoa", debug=False)
