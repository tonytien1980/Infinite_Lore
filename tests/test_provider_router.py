import unittest

from workbench.config_store import DEFAULT_CONFIG
from workbench.provider_router import resolve_route_provider


class ProviderRouterTests(unittest.TestCase):
    def test_default_config_includes_enrich_raw_route(self) -> None:
        self.assertEqual(DEFAULT_CONFIG["routes"]["enrich_raw"], "balanced")

    def test_openai_route_is_chosen_over_competing_eligible_provider(self) -> None:
        settings = {
            "providers": [
                {
                    "id": "openai-main",
                    "provider": "openai",
                    "api_key": "sk-test",
                    "enabled": True,
                    "base_url": "",
                    "models": [
                        {"id": "gpt-5.4-mini", "role": "balanced"},
                        {"id": "gpt-5.4", "role": "best_deep"},
                    ],
                },
                {
                    "id": "ollama-local",
                    "provider": "ollama",
                    "api_key": "",
                    "enabled": True,
                    "base_url": "http://127.0.0.1:11434",
                    "models": [
                        {"id": "qwen3:14b", "role": "balanced"},
                        {"id": "qwen3:32b", "role": "best_deep"},
                    ],
                },
            ],
            "routes": {
                "ask": "best_deep",
                "enrich_raw": "balanced",
            },
            "route_provider_preferences": {"ask": ["openai-main", "ollama-local"]},
        }

        route = resolve_route_provider(settings, "ask")

        self.assertEqual(route["provider"], "openai")
        self.assertEqual(route["model"], "gpt-5.4")

    def test_openai_is_selected_when_preferred_local_provider_is_disabled(self) -> None:
        settings = {
            "providers": [
                {
                    "id": "ollama-local",
                    "provider": "ollama",
                    "api_key": "",
                    "enabled": False,
                    "base_url": "http://127.0.0.1:11434",
                    "models": [{"id": "qwen3:14b", "role": "balanced"}],
                },
                {
                    "id": "openai-main",
                    "provider": "openai",
                    "api_key": "sk-test",
                    "enabled": True,
                    "base_url": "",
                    "models": [{"id": "gpt-5.4-mini", "role": "balanced"}],
                },
            ],
            "routes": {"enrich_raw": "balanced"},
            "route_provider_preferences": {"enrich_raw": ["ollama-local", "openai-main"]},
        }

        route = resolve_route_provider(settings, "enrich_raw")

        self.assertEqual(route["provider_id"], "openai-main")
        self.assertEqual(route["model"], "gpt-5.4-mini")

    def test_no_model_route_returns_none(self) -> None:
        settings = {
            "providers": [],
            "routes": {"scan": "no_model"},
            "route_provider_preferences": {},
        }

        self.assertIsNone(resolve_route_provider(settings, "scan"))
