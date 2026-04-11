import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.raw_enrichment import (
    default_enrichment_path,
    default_enrichment_state_path,
    queue_bundle_for_enrichment,
)


class RawEnrichmentQueueTests(unittest.TestCase):
    def test_queue_creates_pending_bundle_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "source-one"
            bundle.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle)

            sidecar = default_enrichment_path(bundle)
            self.assertTrue(sidecar.exists())

            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pending")
            self.assertEqual(payload["provider"], "")
            self.assertEqual(payload["model"], "")

    def test_queue_writes_relative_pending_bundle_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "source-two"
            bundle.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle)

            state_path = default_enrichment_state_path(root)
            self.assertTrue(state_path.exists())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["pending_bundles"][0]["bundle_path"], "20_Raw/inbox/source-two")
            self.assertEqual(state["pending_bundles"][0]["status"], "pending")

    def test_queue_appends_second_bundle_state_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle_one = root / "20_Raw" / "inbox" / "source-three"
            bundle_two = root / "20_Raw" / "inbox" / "source-four"
            bundle_one.mkdir(parents=True)
            bundle_two.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle_one)
            queue_bundle_for_enrichment(root, bundle_two)

            state_path = default_enrichment_state_path(root)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            pending_paths = [entry["bundle_path"] for entry in state["pending_bundles"]]

            self.assertEqual(len(pending_paths), 2)
            self.assertEqual(
                pending_paths,
                [
                    "20_Raw/inbox/source-three",
                    "20_Raw/inbox/source-four",
                ],
            )

    def test_queue_same_bundle_twice_does_not_duplicate_pending_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "source-five"
            bundle.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle)
            queue_bundle_for_enrichment(root, bundle)

            state_path = default_enrichment_state_path(root)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            pending_entries = state["pending_bundles"]

            self.assertEqual(len(pending_entries), 1)
            self.assertEqual(pending_entries[0]["bundle_path"], "20_Raw/inbox/source-five")
            self.assertEqual(pending_entries[0]["status"], "pending")

    def test_queue_persists_state_before_sidecar_when_sidecar_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "source-six"
            bundle.mkdir(parents=True)
            state_path = default_enrichment_state_path(root)
            sidecar_path = default_enrichment_path(bundle)

            original_write = "tools.raw_enrichment._write_json_atomic"

            def fake_write(target_path: Path, payload: dict) -> None:
                if target_path == sidecar_path:
                    raise OSError("disk full while writing sidecar")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with target_path.open("w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                    handle.write("\n")

            with mock.patch(original_write, side_effect=fake_write):
                with self.assertRaises(OSError):
                    queue_bundle_for_enrichment(root, bundle)

            self.assertTrue(state_path.exists())
            self.assertFalse(sidecar_path.exists())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(len(state["pending_bundles"]), 1)
            self.assertEqual(state["pending_bundles"][0]["bundle_path"], "20_Raw/inbox/source-six")
            self.assertEqual(state["pending_bundles"][0]["status"], "pending")

    def test_queue_collapses_existing_duplicate_pending_entries_for_same_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "source-seven"
            bundle.mkdir(parents=True)
            state_path = default_enrichment_state_path(root)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "pending_bundles": [
                            {"bundle_path": "20_Raw/inbox/source-seven", "status": "pending", "provider": "", "model": ""},
                            {"bundle_path": "20_Raw/inbox/source-seven", "status": "failed", "provider": "openai", "model": "gpt-test"},
                            {"bundle_path": "20_Raw/inbox/other-source", "status": "pending", "provider": "", "model": ""},
                        ],
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            queue_bundle_for_enrichment(root, bundle)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            matching_entries = [
                entry for entry in state["pending_bundles"] if entry["bundle_path"] == "20_Raw/inbox/source-seven"
            ]
            self.assertEqual(len(matching_entries), 1)
            self.assertEqual(matching_entries[0]["status"], "pending")
            self.assertEqual(matching_entries[0]["provider"], "")
            self.assertEqual(matching_entries[0]["model"], "")
            self.assertEqual(len(state["pending_bundles"]), 2)

    def test_queue_preserves_malformed_state_file_before_creating_fresh_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "20_Raw" / "inbox" / "source-eight"
            bundle.mkdir(parents=True)
            state_path = default_enrichment_state_path(root)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            corrupt_bytes = b"{not valid json"
            state_path.write_bytes(corrupt_bytes)

            queue_bundle_for_enrichment(root, bundle)

            corrupt_backup = state_path.parent / "raw-enrichment-state.json.corrupt"
            self.assertTrue(corrupt_backup.exists())
            self.assertEqual(corrupt_backup.read_bytes(), corrupt_bytes)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(len(state["pending_bundles"]), 1)
            self.assertEqual(state["pending_bundles"][0]["bundle_path"], "20_Raw/inbox/source-eight")
            self.assertEqual(state["pending_bundles"][0]["status"], "pending")
