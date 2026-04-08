from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "providers": [],
    "routes": {
        "scan": "no_model",
        "import": "no_model",
        "compile": "balanced",
        "ask": "best_deep",
        "reflection": "balanced",
    },
}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return DEFAULT_CONFIG.copy()

    payload = json.loads(path.read_text(encoding="utf-8"))
    config = DEFAULT_CONFIG.copy()
    config.update(payload)
    return config


def save_config(path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return config
