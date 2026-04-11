import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from workbench.background_enrichment import BackgroundEnrichmentWorker


class BackgroundEnrichmentWorkerTests(unittest.TestCase):
    def _make_paths(self) -> tuple[Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        config_path = root / "workbench-config.json"
        config_path.write_text("{}", encoding="utf-8")
        return root, config_path

    def test_run_once_processes_one_bounded_batch_and_returns_result(self) -> None:
        root, config_path = self._make_paths()
        process_pending = mock.Mock(return_value={"processed": 1, "completed": 1})
        worker = BackgroundEnrichmentWorker(
            vault_root=root,
            config_path=config_path,
            batch_size=3,
            process_pending=process_pending,
        )

        result = worker.run_once()

        process_pending.assert_called_once_with(root, config_path, limit=3)
        self.assertEqual(result, {"processed": 1, "completed": 1})

    def test_start_and_stop_toggle_running_state(self) -> None:
        root, config_path = self._make_paths()
        process_pending = mock.Mock(return_value={"processed": 0})
        worker = BackgroundEnrichmentWorker(
            vault_root=root,
            config_path=config_path,
            batch_size=1,
            process_pending=process_pending,
        )

        self.assertFalse(worker.is_running)

        worker.start()
        worker_thread = worker.thread

        self.assertTrue(worker.is_running)

        worker.stop()

        self.assertFalse(worker.is_running)
        self.assertFalse(worker_thread.is_alive())

    def test_stop_keeps_live_thread_visible_until_it_actually_exits(self) -> None:
        root, config_path = self._make_paths()
        entered = threading.Event()
        release = threading.Event()

        def process_pending(_root: Path, _config_path: Path, *, limit: int) -> dict:
            entered.set()
            release.wait()
            return {"processed": limit}

        worker = BackgroundEnrichmentWorker(
            vault_root=root,
            config_path=config_path,
            batch_size=1,
            process_pending=process_pending,
        )

        worker.start()
        self.assertTrue(entered.wait(timeout=1))
        worker_thread = worker.thread

        worker.stop()

        self.assertIs(worker.thread, worker_thread)
        self.assertTrue(worker_thread.is_alive())
        self.assertTrue(worker.is_running)

        release.set()
        worker_thread.join(timeout=2)
        self.assertFalse(worker_thread.is_alive())

        worker.stop()
        self.assertFalse(worker.is_running)
        self.assertIsNone(worker.thread)
