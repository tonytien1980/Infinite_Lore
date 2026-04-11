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
