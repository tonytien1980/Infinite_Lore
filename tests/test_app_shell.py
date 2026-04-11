import json
import tempfile
import sys
import unittest
from unittest import mock
from pathlib import Path

import httpx

from app_shell.main import default_vault_root, resolve_launch_vault_root
from app_shell.state import default_shell_state_path
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

    def test_default_vault_root_forwards_prompt_parent_to_picker_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            selected_vault = temp_root / "Selected Vault"
            selected_vault.mkdir(parents=True)
            seed_vault(selected_vault)

            config_path = temp_root / "config" / "workbench.json"
            prompt_parent = mock.Mock()
            existing_non_vault = temp_root / "existing-non-vault"
            existing_non_vault.mkdir(parents=True)

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=existing_non_vault,
            ), mock.patch("app_shell.main.prompt_for_vault_root", return_value=selected_vault) as prompt_for_vault_root:
                resolved = default_vault_root(config_path=config_path, prompt_parent=prompt_parent)

            self.assertEqual(resolved, selected_vault.resolve())
            prompt_for_vault_root.assert_called_once_with(prompt_parent)

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

    def test_launch_app_uses_controller_driven_startup_handoff(self) -> None:
        from app_shell.main import launch_app

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with mock.patch("app_shell.main.AppShellController") as controller_cls:
                controller = controller_cls.return_value

                launch_app(vault_root=root, config_path=root / "workbench.json")

            controller_cls.assert_called_once_with(
                config_path=root / "workbench.json",
                initial_vault_root=root,
            )
            controller.run.assert_called_once()

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

    def test_resolve_launch_vault_root_uses_saved_state_when_auto_candidates_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            saved_vault = temp_root / "Saved Vault"
            saved_vault.mkdir(parents=True)
            seed_vault(saved_vault)

            config_path = temp_root / "config" / "workbench.json"
            state_path = default_shell_state_path(config_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"last_vault_root": str(saved_vault.resolve())}),
                encoding="utf-8",
            )

            self.assertEqual(default_shell_state_path(config_path), state_path)

            existing_non_vault = temp_root / "existing-non-vault"
            existing_non_vault.mkdir(parents=True)

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=existing_non_vault,
            ), mock.patch("app_shell.main.prompt_for_vault_root") as prompt_for_vault_root:
                resolved = resolve_launch_vault_root(config_path=config_path, prompt_parent=None)

            self.assertEqual(resolved, saved_vault.resolve())
            prompt_for_vault_root.assert_not_called()

    def test_resolve_launch_vault_root_prompts_and_saves_valid_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            selected_vault = temp_root / "Chosen Vault"
            selected_vault.mkdir(parents=True)
            seed_vault(selected_vault)

            config_path = temp_root / "config" / "workbench.json"
            state_path = default_shell_state_path(config_path)

            existing_non_vault = temp_root / "existing-non-vault"
            existing_non_vault.mkdir(parents=True)

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=existing_non_vault,
            ), mock.patch(
                "app_shell.main.prompt_for_vault_root",
                return_value=selected_vault,
            ) as prompt_for_vault_root:
                resolved = resolve_launch_vault_root(config_path=config_path, prompt_parent=mock.Mock())

            self.assertEqual(resolved, selected_vault.resolve())
            saved_payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_payload["last_vault_root"], str(selected_vault.resolve()))
            prompt_for_vault_root.assert_called_once()

    def test_resolve_launch_vault_root_raises_product_error_when_picker_is_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            config_path = temp_root / "config" / "workbench.json"
            existing_non_vault = temp_root / "existing-non-vault"
            existing_non_vault.mkdir(parents=True)
            prompt_parent = mock.Mock()

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=existing_non_vault,
            ), mock.patch(
                "app_shell.main.prompt_for_vault_root",
                return_value=None,
            ) as prompt_for_vault_root:
                with self.assertRaisesRegex(RuntimeError, "找不到可用的知識庫資料夾"):
                    resolve_launch_vault_root(config_path=config_path, prompt_parent=prompt_parent)

            prompt_for_vault_root.assert_called_once_with(prompt_parent)

    def test_resolve_launch_vault_root_rejects_invalid_picker_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            invalid_selection = temp_root / "Invalid Vault"
            invalid_selection.mkdir(parents=True)

            config_path = temp_root / "config" / "workbench.json"
            state_path = default_shell_state_path(config_path)
            prompt_parent = mock.Mock()

            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=temp_root / "existing-non-vault",
            ), mock.patch(
                "app_shell.main.prompt_for_vault_root",
                return_value=invalid_selection,
            ) as prompt_for_vault_root:
                with self.assertRaisesRegex(RuntimeError, "不是有效的 Infinite Lore 知識庫"):
                    resolve_launch_vault_root(config_path=config_path, prompt_parent=prompt_parent)

            prompt_for_vault_root.assert_called_once_with(prompt_parent)
            self.assertFalse(state_path.exists())

    def test_resolve_launch_vault_root_falls_through_from_stale_saved_state_to_picker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            stale_saved_vault = temp_root / "Stale Vault"
            stale_saved_vault.mkdir(parents=True)

            config_path = temp_root / "config" / "workbench.json"
            state_path = default_shell_state_path(config_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"last_vault_root": str(stale_saved_vault.resolve())}),
                encoding="utf-8",
            )

            expected_state_path = default_shell_state_path(config_path)
            self.assertEqual(state_path, expected_state_path)
            self.assertEqual(default_shell_state_path(config_path), expected_state_path)

            picked_vault = temp_root / "Picked Vault"
            picked_vault.mkdir(parents=True)
            seed_vault(picked_vault)

            prompt_parent = mock.Mock()
            with mock.patch.object(sys, "frozen", False, create=True), mock.patch.object(
                Path,
                "cwd",
                return_value=temp_root / "existing-non-vault",
            ), mock.patch("app_shell.main.prompt_for_vault_root", return_value=picked_vault) as prompt_for_vault_root:
                resolved = resolve_launch_vault_root(config_path=config_path, prompt_parent=prompt_parent)

            self.assertEqual(resolved, picked_vault.resolve())
            prompt_for_vault_root.assert_called_once_with(prompt_parent)


class AppShellUiTests(unittest.TestCase):
    def test_build_loading_html_uses_traditional_chinese_copy(self) -> None:
        from app_shell.window import build_loading_html

        startup_copy = "正在準備知識庫..."
        html = build_loading_html(startup_copy)

        self.assertIn("Infinite Lore", html)
        self.assertIn(startup_copy, html)
        self.assertNotIn("Loading", html)

    def test_build_error_html_includes_recovery_actions(self) -> None:
        from app_shell.window import build_error_html

        html = build_error_html(
            title="無法開啟知識工作台",
            message="請重新選擇知識庫資料夾。",
            show_retry=True,
            show_choose_vault=True,
        )

        self.assertIn("重新嘗試", html)
        self.assertIn("選擇知識庫資料夾", html)
        self.assertIn("結束應用程式", html)
        self.assertIn("window.pywebview.api.retry_launch()", html)
        self.assertIn("window.pywebview.api.choose_vault()", html)
        self.assertIn('onclick="window.pywebview.api.quit_app()"', html)

    def test_build_error_html_omits_recovery_actions_when_flags_are_false(self) -> None:
        from app_shell.window import build_error_html

        html = build_error_html(
            title="無法開啟知識工作台",
            message="請重新選擇知識庫資料夾。",
            show_retry=False,
            show_choose_vault=False,
        )

        self.assertIn("無法開啟知識工作台", html)
        self.assertIn("請重新選擇知識庫資料夾。", html)
        self.assertIn("結束應用程式", html)
        self.assertNotIn("重新嘗試", html)
        self.assertNotIn("window.pywebview.api.retry_launch()", html)
        self.assertNotIn("window.pywebview.api.choose_vault()", html)

    def test_shell_window_api_forwards_actions_to_controller(self) -> None:
        from app_shell.window import ShellWindowApi

        controller = mock.Mock()
        api = ShellWindowApi(controller)

        api.retry_launch()
        api.choose_vault()
        api.quit_app()

        controller.retry_launch.assert_called_once_with()
        controller.choose_vault.assert_called_once_with()
        controller.quit_app.assert_called_once_with()

    def test_controller_loads_workbench_url_after_successful_boot(self) -> None:
        from app_shell.main import AppShellController

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            controller = AppShellController(config_path=root / "workbench.json")
            window = mock.Mock()
            controller.window = window
            event_log = []

            with mock.patch(
                "app_shell.main.build_loading_html",
                return_value="loading html",
            ) as build_loading_html, mock.patch(
                "app_shell.main.resolve_launch_vault_root",
                return_value=root.resolve(),
            ) as resolve_launch_vault_root, mock.patch(
                "app_shell.main.EmbeddedWorkbenchServer"
            ) as server_cls:
                server = server_cls.return_value
                server.base_url = "http://127.0.0.1:7788"
                window.load_html.side_effect = lambda html: event_log.append(("load_html", html))
                server.start.side_effect = lambda: event_log.append(("start", None))
                window.load_url.side_effect = lambda url: event_log.append(("load_url", url))

                controller.bootstrap(window)

            self.assertEqual(
                event_log,
                [
                    ("load_html", "loading html"),
                    ("start", None),
                    ("load_url", "http://127.0.0.1:7788"),
                ],
            )
            build_loading_html.assert_called_once()
            resolve_launch_vault_root.assert_called_once()
            _, resolve_kwargs = resolve_launch_vault_root.call_args
            self.assertEqual(resolve_kwargs["config_path"], root / "workbench.json")
            self.assertIn("prompt_parent", resolve_kwargs)
            self.assertIs(resolve_kwargs["prompt_parent"], window)
            server_cls.assert_called_once_with(
                vault_root=root.resolve(),
                config_path=root / "workbench.json",
            )

    def test_controller_renders_error_html_when_server_start_fails(self) -> None:
        from app_shell.main import AppShellController

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_vault(root)
            controller = AppShellController(config_path=root / "workbench.json")
            window = mock.Mock()
            controller.window = window

            with mock.patch(
                "app_shell.main.build_loading_html",
                return_value="loading html",
            ), mock.patch(
                "app_shell.main.resolve_launch_vault_root",
                return_value=root.resolve(),
            ), mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls:
                server = server_cls.return_value
                server.base_url = "http://127.0.0.1:7788"
                server.start.side_effect = RuntimeError("boot failed")

                controller.bootstrap(window)

            window.load_html.assert_called()
            rendered_html = window.load_html.call_args[0][0]
            self.assertIn("無法開啟知識工作台", rendered_html)
            self.assertIn("boot failed", rendered_html)
            self.assertIn("重新嘗試", rendered_html)
            self.assertIn("選擇知識庫資料夾", rendered_html)
            self.assertIn("結束應用程式", rendered_html)
            self.assertIn("window.pywebview.api.retry_launch()", rendered_html)
            self.assertIn("window.pywebview.api.choose_vault()", rendered_html)
            window.load_url.assert_not_called()

    def test_controller_renders_error_html_when_launch_resolution_fails(self) -> None:
        from app_shell.main import AppShellController

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            controller = AppShellController(config_path=root / "workbench.json")
            window = mock.Mock()
            controller.window = window

            with mock.patch(
                "app_shell.main.build_loading_html",
                return_value="loading html",
            ), mock.patch(
                "app_shell.main.resolve_launch_vault_root",
                side_effect=RuntimeError("找不到可用的知識庫資料夾"),
            ), mock.patch("app_shell.main.EmbeddedWorkbenchServer") as server_cls:
                controller.bootstrap(window)

            server_cls.assert_not_called()
            window.load_html.assert_called()
            rendered_html = window.load_html.call_args[0][0]
            self.assertIn("無法開啟知識工作台", rendered_html)
            self.assertIn("找不到可用的知識庫資料夾", rendered_html)
            self.assertIn("重新嘗試", rendered_html)
            self.assertIn("選擇知識庫資料夾", rendered_html)
            self.assertIn("結束應用程式", rendered_html)
            self.assertIn("window.pywebview.api.retry_launch()", rendered_html)
            self.assertIn("window.pywebview.api.choose_vault()", rendered_html)
            self.assertIn('onclick="window.pywebview.api.quit_app()"', rendered_html)
            window.load_url.assert_not_called()
