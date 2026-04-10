from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from PIL import Image, UnidentifiedImageError

from tools.vision_ocr import VisionOcrResult, run_vision_ocr

MAX_OCR_TEXT_CHARS = 1200


@dataclass
class ImageExtractionResult:
    title: str
    markdown: str
    warnings: List[str]
    extraction_confidence: str
    asset_files: List[Tuple[str, bytes]]
    ocr_engine: str
    ocr_attempted: bool
    ocr_status: str
    ocr_text_present: bool
    image_interpretation_mode: str
    image_kind_guess: str


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


def _normalize_ocr_text(text: str) -> str:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()
    if len(normalized) > MAX_OCR_TEXT_CHARS:
        normalized = normalized[:MAX_OCR_TEXT_CHARS].rstrip() + "..."
    return normalized


def _guess_image_kind(width: int, height: int, ocr: VisionOcrResult) -> str:
    has_text = bool(ocr.text.strip())
    lines = [line.lower() for line in ocr.lines if line.strip()]
    looks_document = any(
        token in line
        for line in lines
        for token in ("invoice", "total", "summary", "report", "page", "section", "due")
    )
    looks_ui = any(
        token in line
        for line in lines
        for token in ("menu", "toolbar", "sidebar", "button", "dashboard", "settings", "search")
    )

    if looks_ui and looks_document:
        return "mixed"
    if looks_document:
        return "document-like"
    if looks_ui:
        return "ui-like"
    if has_text and width >= 2 * height:
        return "ui-like"
    if has_text and height >= width:
        return "document-like"
    return "generic-image"


def _ocr_summary_lines(ocr: VisionOcrResult) -> List[str]:
    text_density = "text-light"
    if ocr.line_count >= 8:
        text_density = "text-heavy"
    elif ocr.line_count >= 2:
        text_density = "text-present"

    return [
        f"- OCR engine: `{ocr.engine or 'apple-vision'}`",
        f"- OCR status: `{ocr.status}`",
        f"- Recognized lines: `{ocr.line_count}`",
        f"- Recognized regions: `{ocr.region_count}`",
        f"- Text density guess: `{text_density}`",
    ]


def _screenshot_signal_lines(kind_guess: str) -> List[str]:
    return [
        "- Interpretation mode: `bounded`",
        f"- Image kind guess: `{kind_guess}`",
        "- Screenshot posture: conservative local import-time hints only",
    ]


def _ocr_text_block(ocr: VisionOcrResult) -> str:
    text = _normalize_ocr_text(ocr.text)
    if text:
        return text
    if ocr.warning:
        return f"Warning: {ocr.warning}"
    return "No OCR text was detected from this image."


def extract_image_bundle(path: Path) -> ImageExtractionResult:
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            image_format = (image.format or path.suffix.lstrip(".") or "unknown").upper()
            mode = image.mode or "unknown"
            transparency_note = _describe_transparency(image)
            structural_summary = " ".join(
                [
                    _size_summary(width, height),
                    _color_summary(image),
                    transparency_note,
                ]
            )
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unsupported or unreadable image import: {path}") from exc

    ocr = run_vision_ocr(path)
    kind_guess = _guess_image_kind(width, height, ocr)
    warnings = [
        "image import used bounded summary path",
        "review the original image if exact visual meaning matters",
    ]
    if ocr.status != "success":
        warnings.append("vision-first OCR fallback remained conservative and requires review")
    if ocr.warning:
        warnings.append(ocr.warning.lower())

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
            "## OCR Summary",
            "",
            *_ocr_summary_lines(ocr),
            "",
            "## OCR Text",
            "",
            _ocr_text_block(ocr),
            "",
            "## Screenshot Signals",
            "",
            *_screenshot_signal_lines(kind_guess),
            "",
            "## Extraction Notes",
            "",
            "This first-pass image import preserves the original file and records bounded OCR-aware image understanding signals.",
            "Warnings are retained when OCR is unavailable, partial, or failed so downstream review stays conservative.",
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
        ocr_engine=ocr.engine or "apple-vision",
        ocr_attempted=ocr.status != "unavailable" or bool(ocr.warning) or bool(ocr.engine),
        ocr_status=ocr.status,
        ocr_text_present=bool(_normalize_ocr_text(ocr.text)),
        image_interpretation_mode="bounded",
        image_kind_guess=kind_guess,
    )
