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
    except (OSError, TypeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    raw_value = payload.get("last_vault_root")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    return Path(raw_value).expanduser().resolve()


def save_saved_vault_root(state_path: Path, vault_root: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_vault_root": str(Path(vault_root).expanduser().resolve())}
    state_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
