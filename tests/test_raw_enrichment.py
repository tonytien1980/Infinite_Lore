import json
import tempfile
import unittest
from pathlib import Path

from tools.raw_enrichment import queue_bundle_for_enrichment


class RawEnrichmentQueueTests(unittest.TestCase):
    def test_queue_creates_pending_bundle_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "Raw" / "bundle-001"
            bundle.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle)

            sidecar = bundle / "enrichment.json"
            self.assertTrue(sidecar.exists())

            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pending")
            self.assertEqual(payload["provider"], "")
            self.assertEqual(payload["model"], "")

    def test_queue_writes_relative_pending_bundle_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "Raw" / "bundle-002"
            bundle.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle)

            state_path = root / "00_System" / "raw-enrichment-state.json"
            self.assertTrue(state_path.exists())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["pending_bundles"][0]["bundle_path"], "Raw/bundle-002")
            self.assertEqual(state["pending_bundles"][0]["status"], "pending")

    def test_queue_appends_second_bundle_state_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle_one = root / "Raw" / "bundle-003"
            bundle_two = root / "Raw" / "bundle-004"
            bundle_one.mkdir(parents=True)
            bundle_two.mkdir(parents=True)

            queue_bundle_for_enrichment(root, bundle_one)
            queue_bundle_for_enrichment(root, bundle_two)

            state_path = root / "00_System" / "raw-enrichment-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            pending_paths = [entry["bundle_path"] for entry in state["pending_bundles"]]

            self.assertEqual(len(pending_paths), 2)
            self.assertEqual(pending_paths, ["Raw/bundle-003", "Raw/bundle-004"])

