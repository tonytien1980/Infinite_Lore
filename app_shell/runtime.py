from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Optional

import httpx
import uvicorn

from workbench.server import create_app


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class EmbeddedWorkbenchServer:
    def __init__(
        self,
        vault_root: Path,
        config_path: Path,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
    ) -> None:
        self.vault_root = Path(vault_root).resolve()
        self.config_path = Path(config_path).resolve()
        self.host = host
        self.port = port or _pick_free_port()
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self, timeout: float = 10.0) -> None:
        app = create_app(vault_root=self.vault_root, config_path=self.config_path)
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        self.wait_until_ready(timeout=timeout)

    def wait_until_ready(self, timeout: float = 10.0) -> None:
        deadline = time.time() + timeout
        last_error: Optional[Exception] = None

        while time.time() < deadline:
            try:
                response = httpx.get(f"{self.base_url}/api/system/health", timeout=0.5)
                if response.status_code == 200:
                    return
            except Exception as exc:  # pragma: no cover - surfaced in timeout message
                last_error = exc
            time.sleep(0.1)

        raise RuntimeError(f"Embedded Workbench server did not become ready in time: {last_error}")

    def stop(self, timeout: float = 5.0) -> None:
        if self._server is None:
            return

        self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=timeout)

        self._server = None
        self._thread = None
