import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from workbench.server import create_app


class WorkbenchApiTests(unittest.TestCase):
    def make_client(self, root: Path, config_path: Path) -> TestClient:
        app = create_app(vault_root=root, config_path=config_path)
        return TestClient(app)

    def test_dashboard_returns_core_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            (root / "20_Raw/inbox/example").mkdir()
            (root / "20_Raw/inbox/example/metadata.md").write_text(
                "---\nprimary_domain: ai-application\nsource_refs: []\nconversion_status: converted\n---\n",
                encoding="utf-8",
            )
            (root / "20_Raw/inbox/example/content.md").write_text("hello\n", encoding="utf-8")
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/dashboard")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("bundle_count", payload)
            self.assertIn("knowledge_count", payload)

    def test_import_file_endpoint_creates_bundle_and_wiki_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20_Raw/inbox").mkdir(parents=True)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application").mkdir(parents=True)
            (root / "10_Domains/ai-application/index.md").write_text("# AI Application\n", encoding="utf-8")
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/import-file",
                files={"file": ("sample.txt", b"# Library Systems\n\nA library system organizes knowledge.\n", "text/plain")},
                data={"primary_domain": "ai-application"},
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("bundle_path", payload)
            self.assertTrue((root / payload["bundle_path"]).exists())
            self.assertTrue((root / "30_Wiki/ai-application/library-systems--synthesis.md").exists())

    def test_knowledge_endpoint_lists_synthesis_and_small_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "30_Wiki/ai-application/a-note--synthesis.md").write_text(
                "---\nnote_type: synthesis\nprimary_domain: ai-application\nsource_refs: []\n---\n",
                encoding="utf-8",
            )
            (root / "30_Wiki/ai-application/a-note--concept--knowledge.md").write_text(
                "---\nnote_type: concept\nprimary_domain: ai-application\nsource_refs: []\n---\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/knowledge")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload["synthesis"]), 1)
            self.assertEqual(len(payload["small_notes"]), 1)

    def test_settings_round_trip_persists_model_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            client = self.make_client(root, config_path)

            save_response = client.post(
                "/api/settings",
                json={
                    "providers": [
                        {
                            "id": "openai-main",
                            "provider": "openai",
                            "api_key": "sk-test",
                            "models": [
                                {"id": "gpt-best", "role": "best_deep"},
                                {"id": "gpt-balanced", "role": "balanced"},
                            ],
                        }
                    ],
                    "routes": {
                        "scan": "no_model",
                        "compile": "balanced",
                        "ask": "best_deep",
                    },
                },
            )
            load_response = client.get("/api/settings")

            self.assertEqual(save_response.status_code, 200)
            self.assertEqual(load_response.status_code, 200)
            payload = load_response.json()
            self.assertEqual(payload["routes"]["ask"], "best_deep")
            self.assertEqual(payload["providers"][0]["provider"], "openai")

    def test_ask_endpoint_returns_grounded_result_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "30_Wiki/ai-application").mkdir(parents=True)
            (root / "30_Wiki/ai-application/library-systems--synthesis.md").write_text(
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes knowledge into reusable access points.\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/ask",
                json={"question": "Summarize what my library knows about library systems.", "mode": "auto"},
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("mode", payload)
            self.assertIn("answer", payload)
            self.assertIn("grounding", payload)
            self.assertIn("trace", payload)


if __name__ == "__main__":
    unittest.main()
