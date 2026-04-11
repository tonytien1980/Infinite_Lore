#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import importlib.util
import sys

missing = []
for module_name in ("webview", "PyInstaller"):
    if importlib.util.find_spec(module_name) is None:
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
