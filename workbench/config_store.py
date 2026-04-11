from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "providers": [
        {
            "id": "openai-main",
            "provider": "openai",
            "enabled": True,
            "api_key": "",
            "base_url": "",
            "models": [
                {"id": "gpt-5.4-mini", "role": "balanced"},
                {"id": "gpt-5.4", "role": "best_deep"},
            ],
        }
    ],
    "routes": {
        "scan": "no_model",
        "import": "no_model",
        "enrich_raw": "balanced",
        "compile": "balanced",
        "ask": "best_deep",
        "query": "no_model",
        "reflection": "balanced",
    },
    "route_provider_preferences": {
        "ask": ["openai-main"],
        "enrich_raw": ["openai-main"],
        "compile": [],
        "reflection": ["openai-main"],
    },
}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)

    payload = json.loads(path.read_text(encoding="utf-8"))
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(payload)

    routes = payload.get("routes")
    if isinstance(routes, dict):
        config["routes"].update(routes)

    route_preferences = payload.get("route_provider_preferences")
    if isinstance(route_preferences, dict):
        config["route_provider_preferences"].update(route_preferences)

    return config


def save_config(path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return config
