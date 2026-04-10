import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools.image_adapter import extract_image_bundle


def write_test_png(path: Path, size: tuple[int, int] = (64, 32)) -> None:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    image.save(path, format="PNG")


class ImageAdapterTests(unittest.TestCase):
    def test_successful_ocr_adds_ocr_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ocr-sample.png"
            write_test_png(source)

            completed = subprocess.CompletedProcess(
                args=["tesseract"],
                returncode=0,
                stdout="Alpha Gate\nSecondary Label\n",
                stderr="",
            )

            with patch("tools.image_adapter.shutil.which", return_value="/usr/bin/tesseract"), patch(
                "tools.image_adapter.subprocess.run", return_value=completed
            ):
                result = extract_image_bundle(source)

            self.assertIn("## OCR Summary", result.markdown)
            self.assertIn("## OCR Text", result.markdown)
            self.assertIn("## Screenshot Signals", result.markdown)
            self.assertIn("Alpha Gate", result.markdown)

    def test_fallback_without_ocr_keeps_bounded_image_summary_posture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fallback.png"
            write_test_png(source, size=(12, 12))

            with patch("tools.image_adapter.shutil.which", return_value=None):
                result = extract_image_bundle(source)

            self.assertIn("## OCR Summary", result.markdown)
            self.assertIn("## OCR Text", result.markdown)
            self.assertIn("bounded image summary", result.markdown.lower())
            self.assertIn("review the source image directly", result.markdown.lower())

    def test_screenshot_signals_stay_bounded_and_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "signals.png"
            write_test_png(source, size=(256, 256))

            completed = subprocess.CompletedProcess(
                args=["tesseract"],
                returncode=0,
                stdout="Invoice Header\nTotal Due\n",
                stderr="",
            )

            with patch("tools.image_adapter.shutil.which", return_value="/usr/bin/tesseract"), patch(
                "tools.image_adapter.subprocess.run", return_value=completed
            ):
                result = extract_image_bundle(source)

            self.assertIn("## Screenshot Signals", result.markdown)
            self.assertIn("bounded", result.markdown.lower())
            self.assertIn("conservative", result.markdown.lower())
            self.assertNotIn("guarantees", result.markdown.lower())


if __name__ == "__main__":
    unittest.main()
