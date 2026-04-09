import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from workbench.server import create_app
from workbench.source_store import load_source_state


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
            self.assertIn("reflections", payload)

    def test_reflection_endpoints_draft_and_confirm(self) -> None:
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
                "A library system organizes reusable access points.\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            draft = client.post(
                "/api/ask/reflection/draft",
                json={
                    "question": "What is a library system?",
                    "ask_mode": "ask",
                    "raw_input": "知識入口比堆資料更重要。",
                    "grounding": [
                        {
                            "path": "30_Wiki/ai-application/library-systems--synthesis.md",
                            "title": "Library Systems",
                            "primary_domain": "ai-application",
                        }
                    ],
                },
            )
            payload = draft.json()
            payload.update(
                {
                    "kind": "reflection",
                    "target_ref": payload["linked_note_ref"],
                    "target_note_ref": payload["linked_note_ref"],
                    "target_note_title": payload["linked_note_title"],
                    "proposed_content": payload["body"],
                    "content": payload["body"],
                    "input": payload["raw_input"],
                    "feedback_input": payload["raw_input"],
                }
            )
            saved = client.post("/api/ask/reflection/confirm", json=payload)

            self.assertEqual(draft.status_code, 200)
            self.assertEqual(saved.status_code, 200)
            saved_path = root / saved.json()["path"]
            self.assertTrue(saved_path.exists())
            self.assertIn("50_Brainstorming/reflections/ai-application/", saved.json()["path"])
            saved_text = saved_path.read_text(encoding="utf-8")
            self.assertNotIn("\nkind:", saved_text)
            self.assertNotIn("\ntarget_ref:", saved_text)
            self.assertNotIn("\nproposed_content:", saved_text)

    def test_correction_endpoints_draft_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note_path = root / "30_Wiki/ai-application/library-systems--synthesis.md"
            note_path.parent.mkdir(parents=True)
            note_path.write_text(
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes retrieval.\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            draft = client.post(
                "/api/ask/correction/draft",
                json={
                    "question": "What is a library system?",
                    "ask_mode": "ask",
                    "raw_input": "請改成 reusable access points。",
                    "grounding": [
                        {
                            "path": "30_Wiki/ai-application/library-systems--synthesis.md",
                            "title": "Library Systems",
                            "primary_domain": "ai-application",
                        }
                    ],
                },
            )
            payload = draft.json()
            applied = client.post("/api/ask/correction/apply", json=payload)

            self.assertEqual(draft.status_code, 200)
            self.assertEqual(applied.status_code, 200)
            self.assertEqual(note_path.read_text(encoding="utf-8"), payload["proposed_content"].rstrip() + "\n")
            self.assertIn("80_Archive/wiki-versions/ai-application/", applied.json()["archive_version_ref"])

    def test_correction_apply_rejects_without_pending_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note_path = root / "30_Wiki/ai-application/library-systems--synthesis.md"
            note_path.parent.mkdir(parents=True)
            note_path.write_text(
                "---\n"
                "title: Library Systems\n"
                "note_type: synthesis\n"
                "primary_domain: ai-application\n"
                "source_refs: [\"raw/library\"]\n"
                "---\n\n"
                "# Library Systems\n\n"
                "## Source Summary\n"
                "A library system organizes retrieval.\n",
                encoding="utf-8",
            )
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/ask/correction/apply",
                json={
                    "target_note_ref": "30_Wiki/ai-application/library-systems--synthesis.md",
                    "target_note_title": "Library Systems",
                    "primary_domain": "ai-application",
                    "proposed_content": "not allowed",
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("pending proposal", response.json()["detail"])
            self.assertIn("retrieval", note_path.read_text(encoding="utf-8"))

    def test_reflection_draft_rejects_paths_outside_the_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/ask/reflection/draft",
                json={
                    "question": "What is a library system?",
                    "ask_mode": "ask",
                    "raw_input": "test",
                    "grounding": [
                        {
                            "path": "../outside.md",
                            "title": "Outside",
                            "primary_domain": "ai-application",
                        }
                    ],
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("30_Wiki", response.json()["detail"])

    def test_correction_draft_rejects_non_wiki_targets_inside_the_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00_System").mkdir(parents=True)
            (root / "00_System/Workflow Guide.md").write_text("# Not a wiki note\n", encoding="utf-8")
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/ask/correction/draft",
                json={
                    "question": "What is a library system?",
                    "ask_mode": "ask",
                    "raw_input": "change this",
                    "grounding": [
                        {
                            "path": "00_System/Workflow Guide.md",
                            "title": "Workflow Guide",
                            "primary_domain": "ai-application",
                        }
                    ],
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("30_Wiki", response.json()["detail"])

    def test_sources_round_trip_persists_rss_and_list_page_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            save_response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        },
                        {
                            "id": "list-sej",
                            "name": "Search Engine Journal",
                            "source_type": "article-list-page",
                            "url": "https://www.searchenginejournal.com/category/seo/",
                            "enabled": True,
                        },
                    ]
                },
            )
            load_response = client.get("/api/inbox/sources")

            self.assertEqual(save_response.status_code, 200)
            self.assertEqual(load_response.status_code, 200)
            payload = load_response.json()
            self.assertEqual(len(payload["sources"]), 2)
            self.assertEqual(payload["sources"][0]["source_type"], "rss-feed")
            self.assertEqual(payload["sources"][1]["source_type"], "article-list-page")

    def test_inbox_sources_rejects_invalid_sources_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post("/api/inbox/sources", json={"sources": "not-a-list"})

            self.assertEqual(response.status_code, 400)
            self.assertIn("sources", response.json()["detail"])

    def test_inbox_sources_rejects_missing_sources_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post("/api/inbox/sources", json={})

            self.assertEqual(response.status_code, 400)
            self.assertIn("sources key is required", response.json()["detail"])

    def test_inbox_sources_rejects_malformed_list_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post("/api/inbox/sources", json={"sources": ["bad-entry"]})

            self.assertEqual(response.status_code, 400)
            self.assertIn("each source must be an object", response.json()["detail"])

    def test_inbox_sources_rejects_invalid_source_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "blog-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        }
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("source_type must be one of", response.json()["detail"])

    def test_inbox_sources_rejects_whitespace_only_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "   ",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        }
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("id must be a non-empty string", response.json()["detail"])

    def test_inbox_sources_rejects_whitespace_only_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": " ",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        }
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("name must be a non-empty string", response.json()["detail"])

    def test_inbox_sources_rejects_empty_or_unusable_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            empty_response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-empty",
                            "name": "Empty",
                            "source_type": "rss-feed",
                            "url": "   ",
                            "enabled": True,
                        }
                    ]
                },
            )
            unusable_response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-ftp",
                            "name": "FTP Feed",
                            "source_type": "rss-feed",
                            "url": "ftp://example.com/feed",
                            "enabled": True,
                        }
                    ]
                },
            )

            self.assertEqual(empty_response.status_code, 400)
            self.assertEqual(unusable_response.status_code, 400)
            self.assertIn("url must be a non-empty http(s) URL", empty_response.json()["detail"])
            self.assertIn("url must be a non-empty http(s) URL", unusable_response.json()["detail"])

    def test_inbox_sources_rejects_whitespace_control_url_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            space_host_response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-space",
                            "name": "Space Host",
                            "source_type": "rss-feed",
                            "url": "https://exa mple.com/feed",
                            "enabled": True,
                        }
                    ]
                },
            )
            newline_response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-newline",
                            "name": "Newline Host",
                            "source_type": "rss-feed",
                            "url": "https://example.com/\nfeed",
                            "enabled": True,
                        }
                    ]
                },
            )

            self.assertEqual(space_host_response.status_code, 400)
            self.assertEqual(newline_response.status_code, 400)
            self.assertIn("url must be a non-empty http(s) URL", space_host_response.json()["detail"])
            self.assertIn("url must be a non-empty http(s) URL", newline_response.json()["detail"])

    def test_inbox_sources_sanitizes_sources_to_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                            "notes": "extra-field",
                        }
                    ]
                },
            )
            payload = client.get("/api/inbox/sources").json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                payload["sources"],
                [
                    {
                        "id": "feed-techcrunch",
                        "name": "TechCrunch",
                        "source_type": "rss-feed",
                        "url": "https://techcrunch.com/feed/",
                        "enabled": True,
                    }
                ],
            )

    def test_inbox_sources_preserves_unknown_top_level_state_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            state_path = config_path.with_name("automation-state.json")
            state_path.write_text(
                '{"sources": [], "last_scan": null, "failed_items": [], "scan_cache": {"cursor": "abc123"}}',
                encoding="utf-8",
            )
            client = self.make_client(root, config_path)

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        }
                    ]
                },
            )

            self.assertEqual(response.status_code, 200)
            saved_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("scan_cache", saved_state)
            self.assertEqual(saved_state["scan_cache"], {"cursor": "abc123"})

    def test_inbox_sources_rejects_duplicate_canonical_equivalent_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "HTTPS://TECHCRUNCH.COM:443/feed/",
                            "enabled": True,
                        },
                        {
                            "id": "list-techcrunch",
                            "name": "TechCrunch Mirror",
                            "source_type": "article-list-page",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        },
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("duplicate source url", response.json()["detail"])

    def test_inbox_sources_rejects_duplicate_urls_with_fragment_difference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/#top",
                            "enabled": True,
                        },
                        {
                            "id": "list-techcrunch",
                            "name": "TechCrunch Mirror",
                            "source_type": "article-list-page",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        },
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("duplicate source url", response.json()["detail"])

    def test_inbox_sources_rejects_duplicate_urls_with_empty_path_vs_slash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-home",
                            "name": "Home",
                            "source_type": "rss-feed",
                            "url": "https://example.com",
                            "enabled": True,
                        },
                        {
                            "id": "feed-home-copy",
                            "name": "Home Copy",
                            "source_type": "article-list-page",
                            "url": "https://example.com/",
                            "enabled": True,
                        },
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("duplicate source url", response.json()["detail"])

    def test_inbox_sources_persists_ipv6_literal_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-ipv6",
                            "name": "IPv6 Feed",
                            "source_type": "rss-feed",
                            "url": "https://[2001:db8::1]/feed/",
                            "enabled": True,
                        }
                    ]
                },
            )
            payload = client.get("/api/inbox/sources").json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(payload["sources"][0]["url"], "https://[2001:db8::1]/feed/")

    def test_inbox_sources_rejects_duplicate_source_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        },
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch Duplicate",
                            "source_type": "article-list-page",
                            "url": "https://www.searchenginejournal.com/category/seo/",
                            "enabled": True,
                        },
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("duplicate source id", response.json()["detail"])

    def test_inbox_sources_rejects_duplicate_normalized_source_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.post(
                "/api/inbox/sources",
                json={
                    "sources": [
                        {
                            "id": "feed-techcrunch",
                            "name": "TechCrunch",
                            "source_type": "rss-feed",
                            "url": "https://techcrunch.com/feed/",
                            "enabled": True,
                        },
                        {
                            "id": "list-techcrunch",
                            "name": "TechCrunch Mirror",
                            "source_type": "article-list-page",
                            "url": " https://techcrunch.com/feed/ ",
                            "enabled": True,
                        },
                    ]
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("duplicate source url", response.json()["detail"])

    def test_inbox_summary_deduplicates_persisted_duplicate_identity_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            duplicate_id_config = root / "workbench-config-id.json"
            duplicate_id_config.with_name("automation-state.json").write_text(
                '{"sources": ['
                '{"id": "feed-techcrunch", "name": "TechCrunch", "source_type": "rss-feed", "url": "https://techcrunch.com/feed/", "enabled": true},'
                '{"id": "feed-techcrunch", "name": "TechCrunch Copy", "source_type": "article-list-page", "url": "https://www.searchenginejournal.com/category/seo/", "enabled": true}'
                '], "last_scan": null, "failed_items": []}',
                encoding="utf-8",
            )
            duplicate_id_response = self.make_client(root, duplicate_id_config).get("/api/inbox/summary")

            duplicate_url_config = root / "workbench-config-url.json"
            duplicate_url_config.with_name("automation-state.json").write_text(
                '{"sources": ['
                '{"id": "feed-techcrunch", "name": "TechCrunch", "source_type": "rss-feed", "url": "HTTPS://TECHCRUNCH.COM:443/feed/", "enabled": true},'
                '{"id": "list-techcrunch", "name": "TechCrunch Mirror", "source_type": "article-list-page", "url": "https://techcrunch.com/feed/", "enabled": true}'
                '], "last_scan": null, "failed_items": []}',
                encoding="utf-8",
            )
            duplicate_url_response = self.make_client(root, duplicate_url_config).get("/api/inbox/summary")

            self.assertEqual(duplicate_id_response.status_code, 200)
            duplicate_id_payload = duplicate_id_response.json()
            self.assertTrue(duplicate_id_payload["recovered_from_corruption"])
            self.assertEqual(duplicate_id_payload["state_warning"], "recovered_from_corruption")
            self.assertEqual(len(duplicate_id_payload["sources"]), 1)
            self.assertEqual(duplicate_id_payload["sources"][0]["id"], "feed-techcrunch")

            self.assertEqual(duplicate_url_response.status_code, 200)
            duplicate_url_payload = duplicate_url_response.json()
            self.assertTrue(duplicate_url_payload["recovered_from_corruption"])
            self.assertEqual(duplicate_url_payload["state_warning"], "recovered_from_corruption")
            self.assertEqual(len(duplicate_url_payload["sources"]), 1)
            self.assertEqual(duplicate_url_payload["sources"][0]["url"], "https://techcrunch.com/feed/")

    def test_inbox_summary_handles_malformed_source_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            (config_path.with_name("automation-state.json")).write_text("{not-json", encoding="utf-8")
            client = self.make_client(root, config_path)

            response = client.get("/api/inbox/summary")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["sources"], [])
            self.assertEqual(payload["last_scan"], None)
            self.assertEqual(payload["failed_count"], 0)
            self.assertEqual(payload["failed_items"], [])
            self.assertTrue(payload["recovered_from_corruption"])
            self.assertEqual(payload["state_warning"], "recovered_from_corruption")

    def test_inbox_summary_normalizes_null_failed_items_to_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            (config_path.with_name("automation-state.json")).write_text(
                '{"sources": [], "last_scan": null, "failed_items": null}',
                encoding="utf-8",
            )
            client = self.make_client(root, config_path)

            response = client.get("/api/inbox/summary")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["sources"], [])
            self.assertEqual(payload["last_scan"], None)
            self.assertEqual(payload["failed_count"], 0)
            self.assertEqual(payload["failed_items"], [])
            self.assertTrue(payload["recovered_from_corruption"])
            self.assertEqual(payload["state_warning"], "recovered_from_corruption")

    def test_inbox_summary_normalizes_bad_runtime_state_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            (config_path.with_name("automation-state.json")).write_text(
                '{"sources": [], "last_scan": "bad", "failed_items": ["oops"]}',
                encoding="utf-8",
            )
            client = self.make_client(root, config_path)

            response = client.get("/api/inbox/summary")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["sources"], [])
            self.assertEqual(payload["last_scan"], None)
            self.assertEqual(payload["failed_count"], 0)
            self.assertEqual(payload["failed_items"], [])
            self.assertTrue(payload["recovered_from_corruption"])
            self.assertEqual(payload["state_warning"], "recovered_from_corruption")

    def test_inbox_summary_returns_source_and_scan_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = self.make_client(root, root / "workbench-config.json")

            response = client.get("/api/inbox/summary")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("sources", payload)
            self.assertIn("last_scan", payload)
            self.assertIn("failed_count", payload)

    def test_scan_now_endpoint_returns_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            config_path.with_name("automation-state.json").write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "feed-techcrunch",
                                "name": "TechCrunch",
                                "source_type": "rss-feed",
                                "url": "https://techcrunch.com/feed/",
                                "enabled": True,
                            }
                        ],
                        "last_scan": None,
                        "failed_items": [],
                    }
                ),
                encoding="utf-8",
            )
            client = self.make_client(root, config_path)

            response = client.post("/api/inbox/scan")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("ran_at", payload)
            self.assertIn("discovered_count", payload)
            self.assertIn("imported_count", payload)
            self.assertIn("compiled_count", payload)
            self.assertIn("failed_count", payload)
            self.assertIn("retry_limit", payload)

    def test_scan_now_refreshes_summary_with_latest_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            config_path.with_name("automation-state.json").write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "feed-techcrunch",
                                "name": "TechCrunch",
                                "source_type": "rss-feed",
                                "url": "https://techcrunch.com/feed/",
                                "enabled": True,
                            }
                        ],
                        "last_scan": None,
                        "failed_items": [],
                    }
                ),
                encoding="utf-8",
            )
            client = self.make_client(root, config_path)

            scan_response = client.post("/api/inbox/scan")
            summary_response = client.get("/api/inbox/summary")

            self.assertEqual(scan_response.status_code, 200)
            self.assertEqual(summary_response.status_code, 200)
            scan_payload = scan_response.json()
            summary_payload = summary_response.json()
            self.assertEqual(len(summary_payload["sources"]), 1)
            self.assertEqual(summary_payload["sources"][0]["id"], "feed-techcrunch")
            self.assertEqual(summary_payload["last_scan"]["ran_at"], scan_payload["ran_at"])
            self.assertEqual(summary_payload["last_scan"]["retry_limit"], scan_payload["retry_limit"])

    def test_scan_now_uses_latest_saved_sources_after_sources_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            client = self.make_client(root, config_path)

            with mock.patch("workbench.server.run_inbox_scan", return_value={"ran_at": "2026-04-10T00:00:00Z"}) as run_scan:
                save_response = client.post(
                    "/api/inbox/sources",
                    json={
                        "sources": [
                            {
                                "id": "feed-techcrunch",
                                "name": "TechCrunch",
                                "source_type": "rss-feed",
                                "url": "https://techcrunch.com/feed/",
                                "enabled": True,
                            }
                        ]
                    },
                )
                scan_response = client.post("/api/inbox/scan")

            self.assertEqual(save_response.status_code, 200)
            self.assertEqual(scan_response.status_code, 200)
            run_scan.assert_called_once()

            source_state = load_source_state(config_path.with_name("automation-state.json"))
            self.assertEqual(len(source_state["sources"]), 1)
            self.assertEqual(source_state["sources"][0]["id"], "feed-techcrunch")

    def test_scan_now_drops_stale_configured_source_state_when_source_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "workbench-config.json"
            state_path = config_path.with_name("automation-state.json")
            disabled_source = {
                "id": "feed-techcrunch",
                "name": "TechCrunch",
                "source_type": "rss-feed",
                "url": "https://techcrunch.com/feed/",
                "enabled": False,
            }
            state_path.write_text(
                json.dumps(
                    {
                        "sources": [disabled_source],
                        "last_scan": None,
                        "failed_items": [
                            {
                                "source_key": "configured-source:feed-techcrunch",
                                "source": disabled_source["url"],
                                "source_url": disabled_source["url"],
                                "url": disabled_source["url"],
                                "content_hash": "",
                                "primary_domain": "ai-application",
                                "related_domains": [],
                                "stage": "discovery-failed",
                                "error_stage": "fetch",
                                "retry_count": 1,
                                "bundle_path": "",
                            }
                        ],
                        "exhausted_failed_items": [
                            {
                                "source_key": "configured-article:https://example.com/posts/alpha",
                                "source": "https://example.com/posts/alpha",
                                "source_url": disabled_source["url"],
                                "url": "https://example.com/posts/alpha",
                                "content_hash": "",
                                "primary_domain": "ai-application",
                                "related_domains": [],
                                "stage": "imported",
                                "error_stage": "compile",
                                "retry_count": 2,
                                "bundle_path": "",
                            }
                        ],
                        "processed_sources": {},
                    }
                ),
                encoding="utf-8",
            )
            client = self.make_client(root, config_path)

            response = client.post("/api/inbox/scan")

            self.assertEqual(response.status_code, 200)
            payload = load_source_state(state_path)
            self.assertEqual(payload["failed_items"], [])
            self.assertEqual(payload["exhausted_failed_items"], [])


if __name__ == "__main__":
    unittest.main()
