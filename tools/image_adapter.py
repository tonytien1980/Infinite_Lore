from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageFile, UnidentifiedImageError


@dataclass
class ImageExtractionResult:
    title: str
    markdown: str
    warnings: List[str]
    extraction_confidence: str
    asset_files: List[Tuple[str, bytes]]


def _human_title(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").strip().title() or "Imported Image"


def _describe_transparency(image: Image.Image) -> str:
    if "A" in image.getbands():
        return "Transparency channel detected."
    if image.info.get("transparency") is not None:
        return "Indexed transparency detected."
    return "No transparency metadata detected."


def extract_image_bundle(path: Path) -> ImageExtractionResult:
    try:
        previous_truncated_setting = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            image_format = (image.format or path.suffix.lstrip(".") or "unknown").upper()
            mode = image.mode or "unknown"
            transparency_note = _describe_transparency(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unsupported or unreadable image import: {path}") from exc
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = previous_truncated_setting

    markdown = "\n".join(
        [
            "# Image Import",
            "",
            "## Source Summary",
            "",
            f"- Filename: `{path.name}`",
            f"- Format: `{image_format}`",
            f"- Dimensions: `{width} x {height}` pixels",
            f"- Color mode: `{mode}`",
            f"- Transparency: {transparency_note}",
            "",
            "## Extraction Notes",
            "",
            "This first-pass image import preserves the original file and records bounded image metadata.",
            "No OCR text was extracted in this phase. Review the source image directly if text, labels, or layout details matter.",
            "",
        ]
    )

    return ImageExtractionResult(
        title=_human_title(path),
        markdown=markdown,
        warnings=[
            "image import used metadata-only summary",
            "ocr text extraction is not available in this phase",
        ],
        extraction_confidence="low",
        asset_files=[],
    )
