import tempfile
import time
import sys
import unittest
from unittest import mock
from pathlib import Path

import httpx

from app_shell.main import default_vault_root
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

    def test_embedded_server_cleans_up_when_readiness_check_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            server = EmbeddedWorkbenchServer(vault_root=root, config_path=root / "workbench.json")

            mock_server = mock.Mock()
            mock_thread = mock.Mock()
            with mock.patch("app_shell.runtime.uvicorn.Server", return_value=mock_server), mock.patch(
                "app_shell.runtime.threading.Thread", return_value=mock_thread
            ), mock.patch.object(server, "wait_until_ready", side_effect=RuntimeError("boom")):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    server.start()

            self.assertTrue(mock_server.should_exit)
            mock_thread.join.assert_called_once()


class AppShellLaunchTests(unittest.TestCase):
    def test_default_vault_root_uses_frozen_app_bundle_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault_root = Path(tmp)
            (vault_root / "10_Domains").mkdir(parents=True)
            (vault_root / "30_Wiki").mkdir(parents=True)

            executable = vault_root / "dist/Infinite Lore.app/Contents/MacOS/Infinite Lore"
            executable.parent.mkdir(parents=True)
            executable.write_text("", encoding="utf-8")

            with tempfile.TemporaryDirectory() as cwd_tmp:
                cwd_root = Path(cwd_tmp)
                with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
                    sys, "executable", str(executable)
                ), mock.patch.object(Path, "cwd", return_value=cwd_root):
                    self.assertEqual(default_vault_root(), vault_root.resolve())

    def test_launch_app_starts_server_then_opens_window(self) -> None:
        from app_shell.main import launch_app

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)

            with mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls, mock.patch(
                "app_shell.main.open_main_window"
            ) as open_window:
                server = server_cls.return_value
                server.base_url = "http://127.0.0.1:9999"

                launch_app(vault_root=root, config_path=root / "workbench.json")

                server.start.assert_called_once()
                open_window.assert_called_once_with("http://127.0.0.1:9999")

    def test_launch_app_surfaces_startup_failure(self) -> None:
        from app_shell.main import launch_app

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)

            with mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls, mock.patch(
                "app_shell.main.open_error_dialog"
            ) as open_error:
                server = server_cls.return_value
                server.start.side_effect = RuntimeError("boot failed")

                with self.assertRaises(RuntimeError):
                    launch_app(vault_root=root, config_path=root / "workbench.json")

                open_error.assert_called_once()
