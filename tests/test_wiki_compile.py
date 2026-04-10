import json
import tempfile
import unittest
from pathlib import Path

from tools.import_bundle import import_source
from tools.wiki_compile import compile_bundle


class WikiCompileTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_compile_creates_synthesis_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text(
                "---\n"
                "title: AI Application\n"
                "layer: domain-index\n"
                "note_type: domain-index\n"
                "primary_domain: ai-application\n"
                "related_domains: []\n"
                "privacy: private\n"
                "status: active\n"
                "created_at: 2026-04-08\n"
                "updated_at: 2026-04-08\n"
                "source_refs: []\n"
                "---\n\n"
                "# AI Application\n",
                encoding="utf-8",
            )
            source = root / "note.txt"
            source.write_text(
                "# Knowledge Compilation\n\nKnowledge compilation helps transform raw material into reusable notes.\n\nWhat makes a source-grounded synthesis trustworthy?\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "ai-application")

            result = compile_bundle(root, bundle)

            synthesis_path = root / result["synthesis_path"]
            self.assertTrue(synthesis_path.exists())
            synthesis = self.read(synthesis_path)
            self.assertIn("## Source Summary", synthesis)
            self.assertIn("## Key Points", synthesis)
            self.assertIn("## Source Lineage", synthesis)

    def test_compile_extracts_and_writes_question_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/management").mkdir(parents=True)
            (root / "10_Domains/management").mkdir(parents=True)
            (root / "10_Domains/management/index.md").write_text("# Management\n", encoding="utf-8")
            source = root / "question.txt"
            source.write_text(
                "# Team Decisions\n\nHow should a team make faster decisions?\n\nA good decision process should be reusable.\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "management")

            result = compile_bundle(root, bundle)

            self.assertTrue(result["small_note_paths"])
            note_text = self.read(root / result["small_note_paths"][0])
            self.assertIn("note_type: question", note_text)
            self.assertIn("How should a team make faster decisions?", note_text)

    def test_compile_merges_matching_small_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")

            existing = root / "30_Wiki/ai-application/old-source--concept--knowledge-compilation.md"
            existing.write_text(
                "---\n"
                "id: old-source--concept--knowledge-compilation\n"
                "title: Knowledge Compilation\n"
                "layer: wiki\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "related_domains: []\n"
                "privacy: private\n"
                "status: active\n"
                "created_at: 2026-04-08\n"
                "updated_at: 2026-04-08\n"
                "source_refs: [\"raw/old\"]\n"
                "confidence: medium\n"
                "last_compiled_at: 2026-04-08T00:00:00Z\n"
                "last_reviewed_at:\n"
                "raw_bundle_ref:\n"
                "compiled_from:\n"
                "---\n\n"
                "# Knowledge Compilation\n\n"
                "## Definition\nExisting definition.\n\n"
                "## Supporting Evidence\n- Existing evidence.\n\n"
                "## Source Lineage\n- raw/old\n",
                encoding="utf-8",
            )

            source = root / "new.txt"
            source.write_text(
                "# Knowledge Compilation\n\nKnowledge compilation helps turn source material into reusable knowledge.\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "ai-application")

            result = compile_bundle(root, bundle)

            self.assertEqual(len(result["small_note_paths"]), 1)
            self.assertEqual(
                result["small_note_paths"][0],
                "30_Wiki/ai-application/old-source--concept--knowledge-compilation.md",
            )
            merged_text = self.read(existing)
            self.assertIn(
                "Knowledge compilation helps turn source material into reusable knowledge.",
                merged_text,
            )

    def test_compile_updates_bundle_metadata_and_domain_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/business-strategy").mkdir(parents=True)
            (root / "10_Domains/business-strategy").mkdir(parents=True)
            index_path = root / "10_Domains/business-strategy/index.md"
            index_path.write_text("# Business Strategy\n", encoding="utf-8")
            source = root / "strategy.txt"
            source.write_text(
                "# Repeatable Strategy\n\nA repeatable strategy helps teams focus.\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "business-strategy")

            result = compile_bundle(root, bundle)

            metadata_text = self.read(bundle / "metadata.md")
            index_text = self.read(index_path)
            self.assertIn("compiled_at:", metadata_text)
            self.assertIn("compiled_note_refs:", metadata_text)
            self.assertIn(result["synthesis_path"], metadata_text)
            self.assertIn("## Recently Compiled", index_text)
            self.assertIn("repeatable-strategy--synthesis", index_text)

    def test_compile_refreshes_relation_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            wiki_dir = root / "30_Wiki/ai-application"
            wiki_dir.mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")

            source = root / "shared-source.txt"
            source.write_text(
                "# Knowledge Graphs\n\nRelation-aware retrieval should surface linked notes.\n",
                encoding="utf-8",
            )
            source_ref = str(source)
            existing = wiki_dir / "linked-concept.md"
            existing.write_text(
                "---\n"
                "id: linked-concept\n"
                "title: Linked Concept\n"
                "layer: wiki\n"
                "note_type: concept\n"
                "primary_domain: ai-application\n"
                "related_domains: []\n"
                "privacy: private\n"
                "status: active\n"
                "created_at: 2026-04-08T00:00:00Z\n"
                "updated_at: 2026-04-08T00:00:00Z\n"
                f'source_refs: ["{source_ref}"]\n'
                "confidence: medium\n"
                "last_compiled_at: 2026-04-08T00:00:00Z\n"
                "last_reviewed_at:\n"
                "raw_bundle_ref: 20_Raw/inbox/linked-concept\n"
                "compiled_from: 20_Raw/inbox/linked-concept/content.md\n"
                "---\n\n# Linked Concept\n",
                encoding="utf-8",
            )
            bundle = import_source(root, str(source), "ai-application")

            result = compile_bundle(root, bundle)

            relation_index_path = root / "00_System/relation-index.json"
            self.assertTrue(relation_index_path.exists())
            relation_index = json.loads(relation_index_path.read_text(encoding="utf-8"))
            self.assertIn(result["synthesis_path"], {note["path"] for note in relation_index["notes"]})
            self.assertTrue(
                any(
                    edge["relation"] == "shares-source"
                    and result["synthesis_path"] in {edge["source_note"], edge["target_note"]}
                    for edge in relation_index["edges"]
                )
            )


if __name__ == "__main__":
    unittest.main()
