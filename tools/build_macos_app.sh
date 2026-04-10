#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m PyInstaller --noconfirm packaging/pyinstaller/macos_app.spec
echo "Built: $ROOT/dist/Infinite Lore.app"
