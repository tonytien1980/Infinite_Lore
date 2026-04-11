from __future__ import annotations

from typing import Any, Dict, List, Optional


def _provider_enabled(provider: Dict[str, Any]) -> bool:
    return provider.get("enabled") is not False


def _provider_can_run(provider: Dict[str, Any]) -> bool:
    provider_name = str(provider.get("provider") or "")
    if provider_name == "openai":
        return bool(str(provider.get("api_key") or "").strip())
    if provider_name == "ollama":
        return bool(str(provider.get("base_url") or "").strip())
    return False


def _model_for_role(provider: Dict[str, Any], role: str) -> Optional[str]:
    models = provider.get("models", [])
    if not isinstance(models, list):
        return None

    for model in models:
        if not isinstance(model, dict):
            continue
        if model.get("role") == role and model.get("id"):
            return str(model["id"])
    return None


def _ordered_providers(settings: Dict[str, Any], route_name: str) -> List[Dict[str, Any]]:
    providers = [provider for provider in settings.get("providers", []) if isinstance(provider, dict)]
    preferred_ids = settings.get("route_provider_preferences", {}).get(route_name, [])

    ordered: List[Dict[str, Any]] = []
    if isinstance(preferred_ids, list):
        for provider_id in preferred_ids:
            for provider in providers:
                if provider.get("id") == provider_id and provider not in ordered:
                    ordered.append(provider)

    for provider in providers:
        if provider not in ordered:
            ordered.append(provider)

    return ordered


def resolve_route_provider(settings: Dict[str, Any], route_name: str) -> Optional[Dict[str, str]]:
    role = settings.get("routes", {}).get(route_name)
    if not role or role == "no_model":
        return None

    for provider in _ordered_providers(settings, route_name):
        if not _provider_enabled(provider):
            continue
        if not _provider_can_run(provider):
            continue

        model_id = _model_for_role(provider, str(role))
        if not model_id:
            continue

        return {
            "provider_id": str(provider.get("id") or ""),
            "provider": str(provider.get("provider") or ""),
            "model": model_id,
            "api_key": str(provider.get("api_key") or ""),
            "base_url": str(provider.get("base_url") or ""),
        }

    return None
