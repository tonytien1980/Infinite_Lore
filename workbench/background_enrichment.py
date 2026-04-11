from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from tools.raw_enrichment import process_pending_enrichment


class BackgroundEnrichmentWorker:
    def __init__(
        self,
        *,
        vault_root: Path,
        config_path: Path,
        poll_interval_seconds: int = 15,
        batch_size: int = 1,
        process_pending: Callable[..., Dict[str, Any]] = process_pending_enrichment,
    ) -> None:
        self.vault_root = vault_root
        self.config_path = config_path
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self.process_pending = process_pending
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def thread(self) -> Optional[threading.Thread]:
        return self._thread

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_once(self) -> Dict[str, Any]:
        return self.process_pending(self.vault_root, self.config_path, limit=self.batch_size)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                # Keep the server-owned worker alive and retry on the next poll.
                pass
            self._stop_event.wait(self.poll_interval_seconds)

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="background-raw-enrichment",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        thread = self._thread
        if thread is None:
            return
        self._stop_event.set()
        thread.join(timeout=2)
        self._thread = None
