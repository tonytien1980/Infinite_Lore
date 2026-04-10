import tempfile
import unittest
import json
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

    def write_relation_index(self, root: Path, notes: list[dict], edges: list[dict]) -> None:
        relation_index_path = root / "00_System" / "relation-index.json"
        relation_index_path.parent.mkdir(parents=True, exist_ok=True)
        relation_index_path.write_text(
            json.dumps(
                {
                    "generated_at": "2026-04-10T00:00:00Z",
                    "notes": notes,
                    "edges": edges,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
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

    def test_ask_mode_retrieves_cjk_notes_without_false_abstention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note_path = root / "30_Wiki/ai-application/knowledge-entry--synthesis.md"
            write_note(
                note_path,
                (
                    "---\n"
                    "title: 知識入口\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/cjk\"]\n"
                    "---\n"
                ),
                (
                    "# 知識入口\n\n"
                    "## Source Summary\n"
                    "知識入口是讓使用者更快找到答案的設計。\n"
                ),
            )

            result = answer_question(
                vault_root=root,
                question="知識入口是什麼？",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("知識入口是讓使用者更快找到答案的設計", result["answer"])
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

    def test_local_ask_prefers_synthesis_over_small_note_for_primary_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            synthesis_path = root / "30_Wiki/ai-application/library-systems--synthesis.md"
            synthesis_path.write_text(
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes trusted knowledge access points.\n",
                encoding="utf-8",
            )

            concept_path = root / "30_Wiki/ai-application/library-systems--concept--knowledge-compilation.md"
            concept_path.write_text(
                "---\n"
                "title: Knowledge Compilation\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Knowledge Compilation\n\n"
                "## Definition\n"
                "Knowledge compilation turns raw material into reusable notes.\n",
                encoding="utf-8",
            )

            result = answer_question(
                vault_root=root,
                question="What is a library system?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("trusted knowledge access points", result["answer"])

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

            self.assertIn("目前知識庫中沒有足夠可依據的內容", result["answer"])
            self.assertTrue(result["limits"])
            self.assertIn("目前知識庫中的可用證據不足。", result["limits"])

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
            self.assertIn("目前知識庫中沒有足夠可依據的內容", result["answer"])
            self.assertTrue(result["limits"])
            self.assertIn("目前知識庫中的可用證據不足。", result["limits"])

    def test_relation_aware_retrieval_expands_from_lexical_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/rag-foundations--synthesis.md",
                (
                    "---\n"
                    "title: RAG Foundations\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# RAG Foundations\n\n"
                    "## Source Summary\n"
                    "RAG foundations describe retrieval pipelines.\n"
                ),
            )
            write_note(
                root / "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                (
                    "---\n"
                    "title: Chunking Strategy\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# Chunking Strategy\n\n"
                    "## Definition\n"
                    "Chunking strategy sets note boundaries so retrieval preserves context windows.\n"
                ),
            )
            self.write_relation_index(
                root,
                notes=[
                    {
                        "path": "30_Wiki/ai-application/rag-foundations--synthesis.md",
                        "note_type": "synthesis",
                        "primary_domain": "ai-application",
                    },
                    {
                        "path": "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                        "note_type": "concept",
                        "primary_domain": "ai-application",
                    },
                ],
                edges=[
                    {
                        "source_note": "30_Wiki/ai-application/rag-foundations--synthesis.md",
                        "target_note": "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                        "relation": "derived-from",
                        "confidence": "EXTRACTED",
                    }
                ],
            )

            result = answer_question(
                vault_root=root,
                question="What does my library say about RAG foundations?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            grounding_paths = {note["path"] for note in result["grounding"]}
            self.assertIn("30_Wiki/ai-application/rag-foundations--synthesis.md", grounding_paths)
            self.assertIn(
                "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                grounding_paths,
            )

    def test_relation_aware_retrieval_does_not_override_insufficient_evidence_without_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                (
                    "---\n"
                    "title: Chunking Strategy\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# Chunking Strategy\n\n"
                    "## Definition\n"
                    "Chunking strategy sets note boundaries so retrieval preserves context windows.\n"
                ),
            )
            self.write_relation_index(
                root,
                notes=[
                    {
                        "path": "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                        "note_type": "concept",
                        "primary_domain": "ai-application",
                    }
                ],
                edges=[
                    {
                        "source_note": "30_Wiki/ai-application/nonexistent-anchor.md",
                        "target_note": "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                        "relation": "derived-from",
                        "confidence": "EXTRACTED",
                    }
                ],
            )

            result = answer_question(
                vault_root=root,
                question="What does my library know about wafer pricing?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertEqual(result["grounding"], [])
            self.assertIn("目前知識庫中沒有足夠可依據的內容", result["answer"])
            self.assertTrue(result["limits"])
            self.assertIn("目前知識庫中的可用證據不足。", result["limits"])

    def test_ask_mode_local_answer_uses_traditional_chinese_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed_vault(root)

            result = answer_question(
                vault_root=root,
                question="Summarize what my library knows about library systems.",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("目前可依據的筆記包括：", result["answer"])

    def test_relation_aware_retrieval_ignores_reflection_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/rag-foundations--synthesis.md",
                (
                    "---\n"
                    "title: RAG Foundations\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# RAG Foundations\n\n"
                    "## Source Summary\n"
                    "RAG foundations describe retrieval pipelines.\n"
                ),
            )
            write_note(
                root / "30_Wiki/ai-application/reflection-entry--chunking-gap.md",
                (
                    "---\n"
                    "title: Chunking Gap Reflection\n"
                    "note_type: reflection-entry\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# Chunking Gap Reflection\n\n"
                    "## Reflection\n"
                    "Chunking quality still needs review.\n"
                ),
            )
            self.write_relation_index(
                root,
                notes=[
                    {
                        "path": "30_Wiki/ai-application/rag-foundations--synthesis.md",
                        "note_type": "synthesis",
                        "primary_domain": "ai-application",
                    },
                    {
                        "path": "30_Wiki/ai-application/reflection-entry--chunking-gap.md",
                        "note_type": "reflection-entry",
                        "primary_domain": "ai-application",
                    },
                ],
                edges=[
                    {
                        "source_note": "30_Wiki/ai-application/rag-foundations--synthesis.md",
                        "target_note": "30_Wiki/ai-application/reflection-entry--chunking-gap.md",
                        "relation": "shares-source",
                        "confidence": "INFERRED",
                    }
                ],
            )

            result = answer_question(
                vault_root=root,
                question="What does my library say about RAG foundations?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            grounding_paths = {note["path"] for note in result["grounding"]}
            self.assertIn("30_Wiki/ai-application/rag-foundations--synthesis.md", grounding_paths)
            self.assertNotIn("30_Wiki/ai-application/reflection-entry--chunking-gap.md", grounding_paths)

    def test_relation_aware_retrieval_ignores_outside_vault_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "vault"
            outside = tmp_path / "outside-secret.md"
            write_note(
                root / "30_Wiki/ai-application/anchor--synthesis.md",
                (
                    "---\n"
                    "title: Anchor Note\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/anchor\"]\n"
                    "---\n"
                ),
                (
                    "# Anchor Note\n\n"
                    "## Source Summary\n"
                    "Anchor notes should stay inside the wiki boundary.\n"
                ),
            )
            write_note(
                outside,
                (
                    "---\n"
                    "title: Outside Secret\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/outside\"]\n"
                    "---\n"
                ),
                (
                    "# Outside Secret\n\n"
                    "## Definition\n"
                    "This note lives outside the vault and must never be grounded by Ask.\n"
                ),
            )
            self.write_relation_index(
                root,
                notes=[
                    {
                        "path": "30_Wiki/ai-application/anchor--synthesis.md",
                        "note_type": "synthesis",
                        "primary_domain": "ai-application",
                    }
                ],
                edges=[
                    {
                        "source_note": "30_Wiki/ai-application/anchor--synthesis.md",
                        "target_note": "../outside-secret.md",
                        "relation": "derived-from",
                        "confidence": "EXTRACTED",
                    }
                ],
            )

            result = answer_question(
                vault_root=root,
                question="Explain anchor note",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            grounding_paths = {note["path"] for note in result["grounding"]}
            self.assertIn("30_Wiki/ai-application/anchor--synthesis.md", grounding_paths)
            self.assertNotIn("../outside-secret.md", grounding_paths)

    def test_relation_aware_retrieval_keeps_lexical_anchor_as_primary_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/rag-foundations--synthesis.md",
                (
                    "---\n"
                    "title: RAG Foundations\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# RAG Foundations\n\n"
                    "## Source Summary\n"
                    "RAG foundations describe retrieval pipelines.\n"
                ),
            )
            write_note(
                root / "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                (
                    "---\n"
                    "title: Chunking Strategy\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/rag\"]\n"
                    "---\n"
                ),
                (
                    "# Chunking Strategy\n\n"
                    "## Definition\n"
                    "Chunking strategy sets note boundaries so retrieval preserves context windows.\n"
                ),
            )
            self.write_relation_index(
                root,
                notes=[
                    {
                        "path": "30_Wiki/ai-application/rag-foundations--synthesis.md",
                        "note_type": "synthesis",
                        "primary_domain": "ai-application",
                    },
                    {
                        "path": "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                        "note_type": "concept",
                        "primary_domain": "ai-application",
                    },
                ],
                edges=[
                    {
                        "source_note": "30_Wiki/ai-application/rag-foundations--synthesis.md",
                        "target_note": "30_Wiki/ai-application/rag-foundations--concept--chunking-strategy.md",
                        "relation": "derived-from",
                        "confidence": "EXTRACTED",
                    }
                ],
            )

            result = answer_question(
                vault_root=root,
                question="Explain retrieval",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("RAG foundations describe retrieval pipelines", result["answer"])

    def test_relation_aware_retrieval_deduplicates_path_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/anchor--synthesis.md",
                (
                    "---\n"
                    "title: Anchor Note\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/anchor\"]\n"
                    "---\n"
                ),
                (
                    "# Anchor Note\n\n"
                    "## Source Summary\n"
                    "Anchor note summary.\n"
                ),
            )
            write_note(
                root / "30_Wiki/ai-application/topic--concept.md",
                (
                    "---\n"
                    "title: Topic Note\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/topic\"]\n"
                    "---\n"
                ),
                (
                    "# Topic Note\n\n"
                    "## Definition\n"
                    "Topic note definition.\n"
                ),
            )
            self.write_relation_index(
                root,
                notes=[
                    {
                        "path": "30_Wiki/ai-application/anchor--synthesis.md",
                        "note_type": "synthesis",
                        "primary_domain": "ai-application",
                    },
                    {
                        "path": "30_Wiki/ai-application/topic--concept.md",
                        "note_type": "concept",
                        "primary_domain": "ai-application",
                    },
                ],
                edges=[
                    {
                        "source_note": "30_Wiki/ai-application/anchor--synthesis.md",
                        "target_note": "30_Wiki/ai-application/topic--concept.md",
                        "relation": "derived-from",
                        "confidence": "EXTRACTED",
                    },
                    {
                        "source_note": "30_Wiki/ai-application/anchor--synthesis.md",
                        "target_note": "30_Wiki/ai-application/./topic--concept.md",
                        "relation": "shares-source",
                        "confidence": "INFERRED",
                    },
                ],
            )

            result = answer_question(
                vault_root=root,
                question="Explain anchor note",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            grounding_paths = [note["path"] for note in result["grounding"]]
            self.assertEqual(grounding_paths.count("30_Wiki/ai-application/topic--concept.md"), 1)

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
