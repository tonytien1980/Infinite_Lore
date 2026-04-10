import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.relation_index import build_relation_index, save_relation_index


def write_note(path: Path, metadata: str, body: str = "# Note\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata + "\n" + body, encoding="utf-8")


class RelationIndexTests(unittest.TestCase):
    def test_build_relation_index_returns_generated_at_notes_and_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/library-systems--synthesis.md",
                (
                    "---\n"
                    "title: Library Systems\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/library\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/library\n"
                    "compiled_from: 20_Raw/inbox/library/content.md\n"
                    "---\n"
                ),
                "# Library Systems\n",
            )
            artifact = build_relation_index(root)

            self.assertIn("generated_at", artifact)
            self.assertIn("notes", artifact)
            self.assertIn("edges", artifact)
            self.assertIsInstance(artifact["notes"], list)
            self.assertIsInstance(artifact["edges"], list)
            self.assertEqual(len(artifact["notes"]), 1)
            self.assertEqual(artifact["notes"][0]["path"], "30_Wiki/ai-application/library-systems--synthesis.md")

    def test_extracts_derived_from_edge_from_compiled_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/source--synthesis.md",
                (
                    "---\n"
                    "title: Source Synthesis\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/source\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/source\n"
                    "compiled_from: 20_Raw/inbox/source/content.md\n"
                    "---\n"
                ),
                "# Source Synthesis\n",
            )
            write_note(
                root / "30_Wiki/ai-application/source--concept--foo.md",
                (
                    "---\n"
                    "title: Foo\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/other\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/other\n"
                    "compiled_from: 30_Wiki/ai-application/source--synthesis.md\n"
                    "---\n"
                ),
                "# Foo\n",
            )

            artifact = build_relation_index(root)

            self.assertTrue(
                any(
                    edge["source_note"] == "30_Wiki/ai-application/source--concept--foo.md"
                    and edge["target_note"] == "30_Wiki/ai-application/source--synthesis.md"
                    and edge["relation"] == "derived-from"
                    and edge["confidence"] == "EXTRACTED"
                    and edge["evidence_type"] == "compiled_from"
                    and edge["evidence_ref"] == "30_Wiki/ai-application/source--synthesis.md"
                    for edge in artifact["edges"]
                )
            )

    def test_extracts_shares_source_edge_from_overlapping_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/a--concept.md",
                (
                    "---\n"
                    "title: A\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/shared\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/a\n"
                    "compiled_from: 20_Raw/inbox/a/content.md\n"
                    "---\n"
                ),
                "# A\n",
            )
            write_note(
                root / "30_Wiki/ai-application/b--concept.md",
                (
                    "---\n"
                    "title: B\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/shared\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/b\n"
                    "compiled_from: 20_Raw/inbox/b/content.md\n"
                    "---\n"
                ),
                "# B\n",
            )

            artifact = build_relation_index(root)

            self.assertTrue(
                any(
                    edge["source_note"] == "30_Wiki/ai-application/a--concept.md"
                    and edge["target_note"] == "30_Wiki/ai-application/b--concept.md"
                    and edge["relation"] == "shares-source"
                    and edge["confidence"] == "INFERRED"
                    and edge["evidence_type"] == "source_refs"
                    and edge["evidence_ref"] == "raw/shared"
                    for edge in artifact["edges"]
                )
            )

    def test_extracts_shares_source_edge_from_matching_raw_bundle_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/c--concept.md",
                (
                    "---\n"
                    "title: C\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/c\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/shared\n"
                    "compiled_from: 20_Raw/inbox/c/content.md\n"
                    "---\n"
                ),
                "# C\n",
            )
            write_note(
                root / "30_Wiki/ai-application/d--concept.md",
                (
                    "---\n"
                    "title: D\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/d\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/shared\n"
                    "compiled_from: 20_Raw/inbox/d/content.md\n"
                    "---\n"
                ),
                "# D\n",
            )

            artifact = build_relation_index(root)

            self.assertTrue(
                any(
                    edge["source_note"] == "30_Wiki/ai-application/c--concept.md"
                    and edge["target_note"] == "30_Wiki/ai-application/d--concept.md"
                    and edge["relation"] == "shares-source"
                    and edge["confidence"] == "INFERRED"
                    and edge["evidence_type"] == "raw_bundle_ref"
                    and edge["evidence_ref"] == "20_Raw/inbox/shared"
                    for edge in artifact["edges"]
                )
            )

    def test_excludes_reflection_correction_and_non_wiki_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/kept--concept.md",
                (
                    "---\n"
                    "title: Kept\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/kept\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/kept\n"
                    "compiled_from: 20_Raw/inbox/kept/content.md\n"
                    "---\n"
                ),
                "# Kept\n",
            )
            write_note(
                root / "30_Wiki/ai-application/reflection--entry.md",
                (
                    "---\n"
                    "title: Reflection\n"
                    "note_type: reflection-entry\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/kept\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/reflection\n"
                    "compiled_from: 30_Wiki/ai-application/kept--concept.md\n"
                    "---\n"
                ),
                "# Reflection\n",
            )
            write_note(
                root / "30_Wiki/ai-application/correction--proposal.md",
                (
                    "---\n"
                    "title: Correction\n"
                    "note_type: correction-proposal\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/kept\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/correction\n"
                    "compiled_from: 30_Wiki/ai-application/kept--concept.md\n"
                    "---\n"
                ),
                "# Correction\n",
            )
            write_note(
                root / "10_Domains/ai-application/outside.md",
                (
                    "---\n"
                    "title: Outside\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/kept\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/outside\n"
                    "compiled_from: 30_Wiki/ai-application/kept--concept.md\n"
                    "---\n"
                ),
                "# Outside\n",
            )

            artifact = build_relation_index(root)
            note_paths = {note["path"] for note in artifact["notes"]}

            self.assertIn("30_Wiki/ai-application/kept--concept.md", note_paths)
            self.assertNotIn("30_Wiki/ai-application/reflection--entry.md", note_paths)
            self.assertNotIn("30_Wiki/ai-application/correction--proposal.md", note_paths)
            self.assertNotIn("10_Domains/ai-application/outside.md", note_paths)

    def test_excludes_journal_entry_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/daily--journal-entry.md",
                (
                    "---\n"
                    "title: Daily\n"
                    "note_type: journal-entry\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/daily\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/daily\n"
                    "compiled_from: 20_Raw/inbox/daily/content.md\n"
                    "---\n"
                ),
                "# Daily\n",
            )

            artifact = build_relation_index(root)

            self.assertEqual(artifact["notes"], [])

    def test_excludes_project_log_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/project--project-log.md",
                (
                    "---\n"
                    "title: Project Log\n"
                    "note_type: project-log\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/project\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/project\n"
                    "compiled_from: 20_Raw/inbox/project/content.md\n"
                    "---\n"
                ),
                "# Project Log\n",
            )

            artifact = build_relation_index(root)

            self.assertEqual(artifact["notes"], [])

    def test_excludes_artifact_layer_notes_under_30_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/research--artifact.md",
                (
                    "---\n"
                    "title: Research Artifact\n"
                    "layer: artifact\n"
                    "note_type: deliverable\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/research\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/research\n"
                    "compiled_from: 20_Raw/inbox/research/content.md\n"
                    "---\n"
                ),
                "# Research Artifact\n",
            )

            artifact = build_relation_index(root)

            self.assertEqual(artifact["notes"], [])

    def test_normalizes_compiled_from_with_dot_segment_for_derived_from(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai/source--synthesis.md",
                (
                    "---\n"
                    "title: Source Synthesis\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/source\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/source\n"
                    "compiled_from: 20_Raw/inbox/source/content.md\n"
                    "---\n"
                ),
                "# Source Synthesis\n",
            )
            write_note(
                root / "30_Wiki/ai-application/source--concept--foo.md",
                (
                    "---\n"
                    "title: Foo\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/other\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/other\n"
                    "compiled_from: 30_Wiki/ai/./source--synthesis.md\n"
                    "---\n"
                ),
                "# Foo\n",
            )

            artifact = build_relation_index(root)

            self.assertTrue(
                any(
                    edge["source_note"] == "30_Wiki/ai-application/source--concept--foo.md"
                    and edge["target_note"] == "30_Wiki/ai/source--synthesis.md"
                    and edge["relation"] == "derived-from"
                    for edge in artifact["edges"]
                )
            )

    def test_save_relation_index_skips_noop_rewrite_when_inputs_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(
                root / "30_Wiki/ai-application/library-systems--synthesis.md",
                (
                    "---\n"
                    "title: Library Systems\n"
                    "note_type: synthesis\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/library\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/library\n"
                    "compiled_from: 20_Raw/inbox/library/content.md\n"
                    "---\n"
                ),
                "# Library Systems\n",
            )
            write_note(
                root / "30_Wiki/ai-application/library-systems--concept.md",
                (
                    "---\n"
                    "title: Library Concept\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: [\"raw/library\"]\n"
                    "raw_bundle_ref: 20_Raw/inbox/library\n"
                    "compiled_from: 30_Wiki/ai-application/library-systems--synthesis.md\n"
                    "---\n"
                ),
                "# Library Concept\n",
            )

            with patch("tools.relation_index.now_iso", return_value="2026-04-10T00:00:00Z"):
                first = save_relation_index(root)
            target = root / "00_System/relation-index.json"
            first_text = target.read_text(encoding="utf-8")
            first_mtime = target.stat().st_mtime_ns

            with patch("tools.relation_index.now_iso", return_value="2026-04-10T00:00:01Z"):
                second = save_relation_index(root)
            second_text = target.read_text(encoding="utf-8")
            second_mtime = target.stat().st_mtime_ns

            self.assertEqual(first_text, second_text)
            self.assertEqual(first["generated_at"], second["generated_at"])
            self.assertEqual(first_mtime, second_mtime)


if __name__ == "__main__":
    unittest.main()
