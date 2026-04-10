import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.vision_ocr import run_vision_ocr


class VisionOcrTests(unittest.TestCase):
    def test_run_vision_ocr_parses_success_payload(self) -> None:
        payload = json.dumps(
            {
                "engine": "apple-vision",
                "status": "success",
                "text": "Hello World",
                "lines": ["Hello World"],
                "line_count": 1,
                "region_count": 1,
            }
        )
        completed = subprocess.CompletedProcess(
            args=["swift"],
            returncode=0,
            stdout=payload,
            stderr="",
        )

        with patch("subprocess.run", return_value=completed):
            result = run_vision_ocr(Path("/tmp/sample.png"))

        self.assertEqual(result.engine, "apple-vision")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.text, "Hello World")
        self.assertEqual(result.line_count, 1)

    def test_run_vision_ocr_returns_unavailable_when_swift_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            result = run_vision_ocr(Path("/tmp/sample.png"))

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.text, "")


if __name__ == "__main__":
    unittest.main()
