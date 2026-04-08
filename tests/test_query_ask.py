import tempfile
import unittest
from pathlib import Path

from workbench.ask_service import infer_mode, answer_question


def write_note(path: Path, metadata: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata + "\n" + body, encoding="utf-8")


class QueryAskTests(unittest.TestCase):
    def seed_vault(self, root: Path) -> None:
        write_note(
            root / "30_Wiki/ai-application/library-systems--synthesis.md",
            (
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n"
            ),
            (
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes knowledge into reusable access points.\n\n"
                "## Key Points\n"
                "- It helps retrieval.\n"
                "- It supports grounded answers.\n\n"
                "## Source Lineage\n"
                "- Raw bundle: `20_Raw/inbox/library`\n"
            ),
        )
        write_note(
            root / "30_Wiki/ai-application/library-systems--concept--knowledge-compilation.md",
            (
                "---\n"
                "title: Knowledge Compilation\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n"
            ),
            (
                "# Knowledge Compilation\n\n"
                "## Definition\n"
                "Knowledge compilation turns raw material into reusable notes.\n\n"
                "## Source Lineage\n"
                "- Raw bundle: `20_Raw/inbox/library`\n"
            ),
        )

    def test_infer_mode_prefers_query_for_listing_language(self) -> None:
        self.assertEqual(infer_mode("What notes do I have about library systems?", "auto"), "query")

    def test_infer_mode_prefers_ask_for_summary_language(self) -> None:
        self.assertEqual(infer_mode("Summarize what my library knows about library systems.", "auto"), "ask")

    def test_query_mode_returns_note_matches_without_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="What notes do I have about library systems?",
                requested_mode="query",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertEqual(result["mode"], "query")
            self.assertEqual(result["answer"], "")
            self.assertGreaterEqual(len(result["grounding"]), 1)

    def test_ask_mode_returns_grounded_local_answer_when_no_provider_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="What is knowledge compilation?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertEqual(result["mode"], "ask")
            self.assertIn("Knowledge compilation", result["answer"])
            self.assertGreaterEqual(len(result["grounding"]), 1)
            self.assertGreaterEqual(len(result["trace"]), 1)

    def test_ask_mode_uses_provider_route_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            def fake_generate(**kwargs):
                return "MODEL ANSWER"

            result = answer_question(
                vault_root=root,
                question="What is knowledge compilation?",
                requested_mode="ask",
                settings={
                    "providers": [
                        {
                            "provider": "openai",
                            "api_key": "sk-test",
                            "models": [{"id": "gpt-best", "role": "best_deep"}],
                        }
                    ],
                    "routes": {"query": "no_model", "ask": "best_deep"},
                },
                generate_answer=fake_generate,
            )

            self.assertEqual(result["answer"], "MODEL ANSWER")
            self.assertEqual(result["answer_source"], "model")

    def test_ask_mode_returns_limit_when_evidence_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="What does my library know about semiconductor wafer pricing?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("does not currently contain enough grounded knowledge", result["answer"])
            self.assertTrue(result["limits"])

    def test_ask_mode_does_not_call_model_when_grounding_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            def should_not_run(**kwargs):
                raise AssertionError("model should not be called without grounded notes")

            result = answer_question(
                vault_root=root,
                question="What does my library know about semiconductor wafer pricing?",
                requested_mode="ask",
                settings={
                    "providers": [
                        {
                            "provider": "openai",
                            "api_key": "sk-test",
                            "models": [{"id": "gpt-best", "role": "best_deep"}],
                        }
                    ],
                    "routes": {"query": "no_model", "ask": "best_deep"},
                },
                generate_answer=should_not_run,
            )

            self.assertEqual(result["answer_source"], "local")
            self.assertIn("does not currently contain enough grounded knowledge", result["answer"])
            self.assertTrue(result["limits"])

    def test_ask_mode_ignores_unsupported_provider_routes_for_now(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            def should_not_run(**kwargs):
                raise AssertionError("unsupported providers should not execute the model path")

            result = answer_question(
                vault_root=root,
                question="What is knowledge compilation?",
                requested_mode="ask",
                settings={
                    "providers": [
                        {
                            "provider": "anthropic",
                            "api_key": "sk-test",
                            "models": [{"id": "claude-best", "role": "best_deep"}],
                        }
                    ],
                    "routes": {"query": "no_model", "ask": "best_deep"},
                },
                generate_answer=should_not_run,
            )

            self.assertEqual(result["answer_source"], "local")
            self.assertIn("Knowledge compilation", result["answer"])


if __name__ == "__main__":
    unittest.main()
