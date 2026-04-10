from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from PIL import Image, UnidentifiedImageError

MAX_VISIBLE_TEXT_CHARS = 500


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


def _color_summary(image: Image.Image) -> str:
    colors = image.convert("RGBA").getcolors(maxcolors=256)
    if colors is None:
        return "The image uses a wide range of colors."
    if len(colors) <= 1:
        return "The image appears to be a single-color graphic."
    if len(colors) <= 8:
        return "The image uses a very limited color palette."
    return "The image uses multiple visible colors."


def _size_summary(width: int, height: int) -> str:
    if width <= 8 and height <= 8:
        return "The image is extremely small and likely a tiny asset, icon, or placeholder."
    if width >= height * 1.5:
        return "The image is landscape-oriented."
    if height >= width * 1.5:
        return "The image is portrait-oriented."
    return "The image has a roughly balanced aspect ratio."


def _extract_visible_text(path: Path) -> Tuple[str, str]:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return "", "Visible text extraction is unavailable in this environment."

    try:
        result = subprocess.run(
            [tesseract, str(path), "stdout", "--psm", "6"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "", "Visible text extraction failed for this image."

    text = " ".join(result.stdout.split()).strip()
    if not text:
        return "", "No visible text was detected in this image."
    if len(text) > MAX_VISIBLE_TEXT_CHARS:
        text = text[:MAX_VISIBLE_TEXT_CHARS].rstrip() + "..."
    return text, ""


def extract_image_bundle(path: Path) -> ImageExtractionResult:
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            image_format = (image.format or path.suffix.lstrip(".") or "unknown").upper()
            mode = image.mode or "unknown"
            transparency_note = _describe_transparency(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unsupported or unreadable image import: {path}") from exc

    visible_text, text_note = _extract_visible_text(path)
    warnings = ["image import used bounded summary path", "review the original image if exact visual meaning matters"]
    if text_note:
        warnings.append(text_note.lower())

    structural_summary = " ".join(
        [
            _size_summary(width, height),
            _color_summary(image),
            transparency_note,
        ]
    )

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
            "## Structural Summary",
            "",
            structural_summary,
            "",
            "## Visible Text",
            "",
            visible_text or text_note,
            "",
            "## Extraction Notes",
            "",
            "This first-pass image import preserves the original file and records bounded image understanding signals.",
            "Review the source image directly if exact text, labels, or layout details matter.",
            "",
        ]
    )

    return ImageExtractionResult(
        title=_human_title(path),
        markdown=markdown,
        warnings=warnings,
        extraction_confidence="low",
        asset_files=[],
    )
