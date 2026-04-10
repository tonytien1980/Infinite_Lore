import unittest
from pathlib import Path

from tools.multimodal_detect import MultimodalInputKind, classify_multimodal_input


class MultimodalDetectTests(unittest.TestCase):
    def test_pptx_classifies_as_multimodal_office_input(self) -> None:
        self.assertEqual(
            classify_multimodal_input(Path("deck.pptx")),
            MultimodalInputKind.OFFICE,
        )

    def test_images_classify_as_image_input(self) -> None:
        for filename in ("image.png", "photo.jpg", "photo.jpeg", "preview.webp"):
            with self.subTest(filename=filename):
                self.assertEqual(
                    classify_multimodal_input(Path(filename)),
                    MultimodalInputKind.IMAGE,
                )

    def test_unsupported_files_return_none(self) -> None:
        self.assertIsNone(classify_multimodal_input(Path("notes.txt")))


if __name__ == "__main__":
    unittest.main()
