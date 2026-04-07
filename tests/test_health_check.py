import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.health_check import check_vault


class HealthCheckTests(unittest.TestCase):
    def write(self, root: Path, relative_path: str, content: str) -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def test_accepts_valid_wiki_note_with_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "30_Wiki/ai-application/test.md",
                """
                ---
                title: Test
                layer: wiki
                note_type: concept
                primary_domain: ai-application
                related_domains: []
                privacy: private
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                source_refs:
                  - raw/test
                ---
                # Test
                """,
            )
            report = check_vault(root)
            self.assertEqual(report["errors"], [])

    def test_flags_formal_note_missing_primary_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "30_Wiki/shared/missing-domain.md",
                """
                ---
                title: Missing Domain
                layer: wiki
                note_type: concept
                related_domains: []
                privacy: private
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                source_refs:
                  - raw/test
                ---
                # Missing Domain
                """,
            )
            report = check_vault(root)
            self.assertIn("30_Wiki/shared/missing-domain.md: missing primary_domain", report["errors"])

    def test_flags_wiki_note_missing_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "30_Wiki/business-strategy/no-source.md",
                """
                ---
                title: No Source
                layer: wiki
                note_type: concept
                primary_domain: business-strategy
                related_domains: []
                privacy: private
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                ---
                # No Source
                """,
            )
            report = check_vault(root)
            self.assertIn("30_Wiki/business-strategy/no-source.md: missing source_refs", report["errors"])

    def test_flags_confidential_note_marked_publishable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(
                root,
                "40_Projects/clients/acme/status.md",
                """
                ---
                title: ACME
                layer: project
                note_type: project-status
                primary_domain: consulting
                related_domains: []
                privacy: publishable
                status: active
                created_at: 2026-04-07
                updated_at: 2026-04-07
                source_refs: []
                ---
                # ACME
                """,
            )
            report = check_vault(root)
            self.assertIn(
                "40_Projects/clients/acme/status.md: client path must use privacy client-confidential",
                report["errors"],
            )


if __name__ == "__main__":
    unittest.main()
