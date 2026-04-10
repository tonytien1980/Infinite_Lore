from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import List, Tuple
from xml.etree import ElementTree as ET
from zipfile import ZipFile


PRESENTATION_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class PptxExtractionResult:
    title: str
    markdown: str
    warnings: List[str]
    extraction_confidence: str
    asset_files: List[Tuple[str, bytes]]


def _slide_part_names(archive: ZipFile) -> List[str]:
    presentation_xml = ET.fromstring(archive.read("ppt/presentation.xml"))
    rels_xml = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
    relationship_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_xml.findall("rel:Relationship", PRESENTATION_NS)
    }

    slide_parts: List[str] = []
    for slide_id in presentation_xml.findall("p:sldIdLst/p:sldId", PRESENTATION_NS):
        relationship_id = slide_id.attrib.get(f"{{{PRESENTATION_NS['r']}}}id")
        target = relationship_targets.get(relationship_id or "")
        if not target:
            continue
        slide_parts.append(f"ppt/{target.lstrip('/')}")

    if slide_parts:
        return slide_parts

    return sorted(
        name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")
    )


def _slide_text(slide_xml: bytes) -> List[str]:
    root = ET.fromstring(slide_xml)
    paragraphs: List[str] = []
    for paragraph in root.findall(".//a:p", PRESENTATION_NS):
        runs = [text.text or "" for text in paragraph.findall(".//a:t", PRESENTATION_NS)]
        joined = "".join(runs).strip()
        if joined:
            paragraphs.append(joined)
    return paragraphs


def _extract_media_files(archive: ZipFile) -> List[Tuple[str, bytes]]:
    asset_files: List[Tuple[str, bytes]] = []
    for name in sorted(archive.namelist()):
        if not name.startswith("ppt/media/"):
            continue
        asset_name = Path(name).name
        asset_files.append((f"assets/{asset_name}", archive.read(name)))
    return asset_files


def extract_pptx_bundle(path: Path) -> PptxExtractionResult:
    warnings: List[str] = []
    slide_sections: List[str] = []

    with ZipFile(BytesIO(path.read_bytes())) as archive:
        slide_parts = _slide_part_names(archive)
        if not slide_parts:
            warnings.append("presentation contained no slide parts")

        first_heading = ""
        extracted_slide_count = 0
        for index, part_name in enumerate(slide_parts, start=1):
            paragraphs = _slide_text(archive.read(part_name))
            if not paragraphs:
                warnings.append(f"slide {index} extracted no text")
                continue

            extracted_slide_count += 1
            if not first_heading:
                first_heading = paragraphs[0]

            body = "\n\n".join(paragraphs)
            slide_sections.append(f"## Slide {index}\n\n{body}")

        if slide_sections:
            markdown = "# Presentation Import\n\n" + "\n\n".join(slide_sections) + "\n"
        else:
            markdown = "# Presentation Import\n\nNo extractable slide text was found.\n"

        confidence = "medium" if extracted_slide_count else "low"
        if extracted_slide_count and not warnings:
            confidence = "high"

        return PptxExtractionResult(
            title=first_heading or path.stem.replace("-", " ").replace("_", " ").title() or "Imported Presentation",
            markdown=markdown,
            warnings=warnings,
            extraction_confidence=confidence,
            asset_files=_extract_media_files(archive),
        )
