import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools.image_adapter import extract_image_bundle
from tools.vision_ocr import VisionOcrResult


def write_test_png(path: Path, size: tuple[int, int] = (64, 32)) -> None:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    image.save(path, format="PNG")


class ImageAdapterTests(unittest.TestCase):
    def test_successful_ocr_adds_ocr_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ocr-sample.png"
            write_test_png(source)

            with patch(
                "tools.image_adapter.run_vision_ocr",
                return_value=VisionOcrResult(
                    engine="apple-vision",
                    status="success",
                    text="Alpha Gate\nSecondary Label",
                    lines=["Alpha Gate", "Secondary Label"],
                    line_count=2,
                    region_count=2,
                    warning="",
                ),
            ):
                result = extract_image_bundle(source)

            self.assertIn("## OCR Summary", result.markdown)
            self.assertIn("## OCR Text", result.markdown)
            self.assertIn("## Screenshot Signals", result.markdown)
            self.assertIn("## Extraction Notes", result.markdown)
            self.assertEqual(result.ocr_engine, "apple-vision")
            self.assertTrue(result.ocr_attempted)
            self.assertEqual(result.ocr_status, "success")
            self.assertTrue(result.ocr_text_present)
            self.assertEqual(result.image_interpretation_mode, "bounded")
            self.assertEqual(result.image_kind_guess, "ui-like")

    def test_fallback_without_ocr_keeps_bounded_image_summary_posture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fallback.png"
            write_test_png(source, size=(12, 12))

            with patch(
                "tools.image_adapter.run_vision_ocr",
                return_value=VisionOcrResult(
                    engine="apple-vision",
                    status="unavailable",
                    text="",
                    lines=[],
                    line_count=0,
                    region_count=0,
                    warning="swift runtime unavailable",
                ),
            ):
                result = extract_image_bundle(source)

            self.assertIn("## OCR Summary", result.markdown)
            self.assertIn("## OCR Text", result.markdown)
            self.assertIn("## Structural Summary", result.markdown)
            self.assertIn("## Extraction Notes", result.markdown)
            self.assertIn("warning", result.markdown.lower())
            self.assertEqual(result.ocr_status, "unavailable")
            self.assertFalse(result.ocr_text_present)
            self.assertEqual(result.extraction_confidence, "low")
            self.assertIn("review", " ".join(result.warnings).lower())

    def test_screenshot_signals_stay_bounded_and_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "signals.png"
            write_test_png(source, size=(256, 256))

            with patch(
                "tools.image_adapter.run_vision_ocr",
                return_value=VisionOcrResult(
                    engine="apple-vision",
                    status="success",
                    text="Invoice Header\nTotal Due",
                    lines=["Invoice Header", "Total Due"],
                    line_count=2,
                    region_count=2,
                    warning="",
                ),
            ):
                result = extract_image_bundle(source)

            self.assertIn("## Screenshot Signals", result.markdown)
            self.assertIn("## OCR Summary", result.markdown)
            self.assertIn("## OCR Text", result.markdown)
            self.assertRegex(result.markdown, r"`(ui-like|document-like|mixed|generic-image)`")
            self.assertIn(result.image_kind_guess, {"ui-like", "document-like", "mixed", "generic-image"})


if __name__ == "__main__":
    unittest.main()
