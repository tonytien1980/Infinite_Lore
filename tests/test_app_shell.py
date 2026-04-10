import tempfile
import time
import unittest
from pathlib import Path

import httpx

from app_shell.runtime import EmbeddedWorkbenchServer


def seed_vault(root: Path) -> None:
    (root / "10_Domains/ai-application").mkdir(parents=True, exist_ok=True)
    (root / "10_Domains/ai-application/index.md").write_text(
        "---\nprimary_domain: ai-application\n---\n\n# AI Application\n",
        encoding="utf-8",
    )
    (root / "30_Wiki/ai-application").mkdir(parents=True, exist_ok=True)
    (root / "30_Wiki/ai-application/library-systems--synthesis.md").write_text(
        "---\n"
        "title: Library Systems\n"
        "note_type: synthesis\n"
        "primary_domain: ai-application\n"
        "source_refs: [\"raw/library\"]\n"
        "---\n\n"
        "# Library Systems\n\n"
        "## Source Summary\n"
        "Library systems support grounded answers.\n",
        encoding="utf-8",
    )


class AppShellRuntimeTests(unittest.TestCase):
    def test_embedded_server_starts_and_serves_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            server = EmbeddedWorkbenchServer(vault_root=root, config_path=root / "workbench.json")

            server.start()
            try:
                response = httpx.get(server.base_url, timeout=2.0)
                self.assertEqual(response.status_code, 200)
                self.assertIn('data-page="home"', response.text)
            finally:
                server.stop()

    def test_embedded_server_exposes_health_and_stops_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            server = EmbeddedWorkbenchServer(vault_root=root, config_path=root / "workbench.json")

            server.start()
            try:
                base_url = server.base_url
                response = httpx.get(f"{base_url}/api/system/health", timeout=2.0)
                self.assertEqual(response.status_code, 200)
            finally:
                server.stop()

            with self.assertRaises(httpx.ConnectError):
                httpx.get(base_url, timeout=0.5)
