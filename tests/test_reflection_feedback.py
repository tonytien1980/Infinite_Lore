import tempfile
import unittest
from pathlib import Path

from workbench.ask_service import answer_question
from workbench.reflection_service import (
    apply_correction,
    draft_correction,
    draft_reflection,
    read_note,
    save_reflection,
)


def write_note(path: Path, metadata: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(metadata + "\n" + body, encoding="utf-8")


class ReflectionFeedbackTests(unittest.TestCase):
    def seed_vault(self, root: Path) -> str:
        note_path = root / "30_Wiki/ai-application/library-systems--synthesis.md"
        write_note(
            note_path,
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
                "- It supports retrieval.\n\n"
                "## Source Lineage\n"
                "- Raw bundle: `20_Raw/inbox/library`\n"
            ),
        )
        return note_path.relative_to(root).as_posix()

    def test_non_english_questions_choose_the_matching_grounding_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            distractor_path = root / "30_Wiki/ai-application/data-pool--concept.md"
            write_note(
                distractor_path,
                (
                    "---\n"
                    "title: 資料堆\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: []\n"
                    "---\n"
                ),
                "# 資料堆\n\n## 概述\n這個筆記只談資料堆，不談知識入口。\n",
            )
            relevant_path = root / "30_Wiki/ai-application/knowledge-entry--concept.md"
            write_note(
                relevant_path,
                (
                    "---\n"
                    "title: 知識入口\n"
                    "note_type: concept\n"
                    "primary_domain: ai-application\n"
                    "source_refs: []\n"
                    "---\n"
                ),
                "# 知識入口\n\n## 概述\n知識入口是讓人快速找到答案的方式。\n",
            )
            distractor_note = distractor_path.relative_to(root).as_posix()
            relevant_note = relevant_path.relative_to(root).as_posix()

            draft = draft_reflection(
                vault_root=root,
                ask_question="我想建立知識入口，應該怎麼開始？",
                ask_mode="ask",
                raw_input="我想把知識入口做得更清楚。",
                grounding=[
                    {"path": distractor_note, "title": "資料堆", "primary_domain": "ai-application"},
                    {"path": relevant_note, "title": "知識入口", "primary_domain": "ai-application"},
                ],
            )

            self.assertEqual(draft["linked_note_ref"], relevant_note)

            proposal = draft_correction(
                vault_root=root,
                ask_question="我想建立知識入口，應該怎麼開始？",
                ask_mode="ask",
                raw_input="請把資料堆改成知識入口。",
                grounding=[
                    {"path": distractor_note, "title": "資料堆", "primary_domain": "ai-application"},
                    {"path": relevant_note, "title": "知識入口", "primary_domain": "ai-application"},
                ],
            )

            self.assertEqual(proposal["target_note_ref"], relevant_note)

    def test_draft_reflection_selects_linked_note_and_preserves_raw_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            draft = draft_reflection(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="這讓我想到知識入口應該比知識量更重要。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )

            self.assertEqual(draft["linked_note_ref"], linked_note)
            self.assertEqual(draft["raw_input"], "這讓我想到知識入口應該比知識量更重要。")
            self.assertIn("My Interpretation", draft["body"])

    def test_save_reflection_writes_linked_entry_under_reflections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            draft = draft_reflection(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="知識入口比堆資料更重要。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )
            result = save_reflection(root, draft)

            saved_path = root / result["path"]
            self.assertTrue(saved_path.exists())
            self.assertIn("50_Brainstorming/reflections/ai-application/", result["path"])
            self.assertIn("raw_input:", saved_path.read_text(encoding="utf-8"))

    def test_save_reflection_preserves_multiline_raw_input_without_breaking_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)
            multiline_raw_input = "Line one about the issue.\nLine two with the follow-up."

            draft = draft_reflection(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input=multiline_raw_input,
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )
            result = save_reflection(root, draft)

            saved_text = (root / result["path"]).read_text(encoding="utf-8")
            loaded = read_note(root, result["path"])
            frontmatter = saved_text.split("---\n", 2)[1].split("\n---\n", 1)[0]

            self.assertEqual(loaded["metadata"]["raw_input"], multiline_raw_input)
            self.assertIn("base64:", frontmatter)
            self.assertNotIn("Line two with the follow-up.", frontmatter)

    def test_draft_correction_writes_pending_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)
            original_text = (root / linked_note).read_text(encoding="utf-8")

            proposal = draft_correction(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="請把 retrieval 改成 reusable access。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )

            self.assertNotEqual(proposal["proposed_content"], original_text)
            self.assertIn("reusable access", proposal["proposed_content"].lower())
            pending_path = root / proposal["proposal_path"]
            self.assertTrue(pending_path.exists())
            self.assertIn("50_Brainstorming/corrections/pending/ai-application/", proposal["proposal_path"])
            self.assertIn("proposal_status: pending", pending_path.read_text(encoding="utf-8"))

    def test_draft_correction_fallback_rewrites_the_body_instead_of_appending_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)
            original_text = (root / linked_note).read_text(encoding="utf-8")

            proposal = draft_correction(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="請讓這份筆記更像知識入口，而不是資料堆。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )

            self.assertNotEqual(proposal["proposed_content"], original_text)
            self.assertTrue(proposal["proposed_content"].startswith("---\n"))
            self.assertIn("## Source Summary", proposal["proposed_content"])
            self.assertIn("This revision should emphasize:", proposal["proposed_content"])
            self.assertNotIn("## Correction Notes", proposal["proposed_content"])

    def test_apply_correction_archives_old_version_and_overwrites_live_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)
            original_text = (root / linked_note).read_text(encoding="utf-8")

            proposal = draft_correction(
                vault_root=root,
                ask_question="What is a library system?",
                ask_mode="ask",
                raw_input="請把 retrieval 改成 reusable access。",
                grounding=[{"path": linked_note, "title": "Library Systems", "primary_domain": "ai-application"}],
            )
            proposal["proposed_content"] = (
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes reusable access points for knowledge.\n"
            )
            result = apply_correction(root, proposal)

            live_text = (root / linked_note).read_text(encoding="utf-8")
            archive_text = (root / result["archive_version_ref"]).read_text(encoding="utf-8")
            self.assertIn("reusable access points for knowledge", live_text)
            self.assertEqual(archive_text, original_text)
            self.assertIn("50_Brainstorming/corrections/applied/ai-application/", result["proposal_path"])

    def test_ask_response_returns_reflections_in_recency_order_for_view_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linked_note = self.seed_vault(root)

            reflections_root = root / "50_Brainstorming/reflections/ai-application"
            for stamp, label in [
                ("2026-04-09T10:00:00", "oldest reflection"),
                ("2026-04-09T10:00:01", "older reflection"),
                ("2026-04-09T10:00:02", "newer reflection"),
                ("2026-04-09T10:00:03", "newest reflection"),
            ]:
                slug = label.replace(" ", "-")
                write_note(
                    reflections_root / f"library-systems--reflection--{slug}.md",
                    (
                        "---\n"
                        "title: Reflection - Library Systems\n"
                        "layer: brainstorming\n"
                        "note_type: reflection-entry\n"
                        "primary_domain: ai-application\n"
                        "status: active\n"
                        f"created_at: {stamp}\n"
                        f"updated_at: {stamp}\n"
                        "linked_note_ref: 30_Wiki/ai-application/library-systems--synthesis.md\n"
                        "linked_note_title: Library Systems\n"
                        "ask_question: What is a library system?\n"
                        "ask_mode: ask\n"
                        "grounding_note_refs: [\"30_Wiki/ai-application/library-systems--synthesis.md\"]\n"
                        "source_refs: []\n"
                        "reflection_kind: interpretation\n"
                        f"raw_input: {label}\n"
                        "---\n"
                    ),
                    f"# Reflection\n\n## Triggering Question\nWhat is a library system?\n\n## My Interpretation\n{label}\n",
                )

            result = answer_question(
                vault_root=root,
                question="What is a library system?",
                requested_mode="ask",
                settings={"providers": [], "routes": {"query": "no_model", "ask": "best_deep"}},
            )

            self.assertIn("answer", result)
            self.assertIn("reflections", result)
            self.assertEqual(len(result["reflections"]), 4)
            self.assertEqual(result["reflections"][0]["linked_note_ref"], linked_note)
            self.assertEqual(result["reflections"][0]["created_at"], "2026-04-09T10:00:03")
            self.assertEqual(result["reflections"][3]["created_at"], "2026-04-09T10:00:00")
            self.assertEqual(result["reflections"][3]["linked_note_ref"], linked_note)


if __name__ == "__main__":
    unittest.main()
