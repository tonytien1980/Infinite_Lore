from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET
from zipfile import BadZipFile

from pypdf import PdfReader

from tools.image_adapter import extract_image_bundle
from tools.multimodal_detect import MultimodalInputKind, classify_multimodal_input
from tools.pptx_adapter import extract_pptx_bundle


VAULT_INBOX = Path("20_Raw/inbox")


@dataclass
class ConversionResult:
    title: str
    source_filename: str
    source_bytes: bytes
    content_markdown: str
    source_type: str
    source_ref: str
    source_format: str
    conversion_status: str
    extraction_confidence: str
    review_required: bool
    warnings: List[str]
    asset_paths: List[str]
    asset_files: List[Tuple[str, bytes]]


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def slugify(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered or "import"


def ensure_unique_bundle_path(root: Path, slug: str) -> Path:
    base = root / VAULT_INBOX / f"{date.today().isoformat()}-{slug}"
    if not base.exists():
        return base

    counter = 2
    while True:
        candidate = root / VAULT_INBOX / f"{date.today().isoformat()}-{slug}-{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def detect_source_kind(source: str) -> str:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https", "file"}:
        return "url"
    return "path"


def read_source_bytes(source: str) -> Tuple[bytes, str, str]:
    kind = detect_source_kind(source)
    if kind == "url":
        with urllib.request.urlopen(source) as response:
            data = response.read()
            content_type = response.headers.get_content_type()
            parsed = urllib.parse.urlparse(source)
            extension = Path(parsed.path).suffix.lower()
            if not extension and content_type == "text/html":
                extension = ".html"
            return data, extension or ".bin", content_type

    path = Path(source)
    return path.read_bytes(), path.suffix.lower(), ""


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]

    normalized: List[str] = []
    blank_count = 0
    for line in lines:
        if line.strip():
            blank_count = 0
            normalized.append(line)
        else:
            blank_count += 1
            if blank_count <= 2:
                normalized.append("")

    return "\n".join(normalized).strip() + "\n"


class HtmlToMarkdownParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.output: List[str] = []
        self.current_text: List[str] = []
        self.current_block_tag: Optional[str] = None
        self.list_stack: List[str] = []
        self.ignore_depth = 0
        self.capture_title = False
        self.title_text: List[str] = []
        self.current_link: Optional[str] = None
        self.table_rows: List[List[str]] = []
        self.current_row: Optional[List[str]] = None
        self.current_cell: Optional[List[str]] = None
        self.first_heading: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style"}:
            self.ignore_depth += 1
            return

        if self.ignore_depth:
            return

        if tag == "title":
            self.capture_title = True
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "pre"}:
            self.flush_block()
            self.current_block_tag = tag
            return

        if tag in {"ul", "ol"}:
            self.list_stack.append(tag)
            return

        if tag == "li":
            self.flush_block()
            self.current_block_tag = "li"
            marker = "- " if not self.list_stack or self.list_stack[-1] == "ul" else "1. "
            self.current_text.append(marker)
            return

        if tag == "br":
            self.current_text.append("\n")
            return

        if tag == "a":
            for key, value in attrs:
                if key == "href":
                    self.current_link = value
                    break
            return

        if tag == "tr":
            self.current_row = []
            return

        if tag in {"th", "td"}:
            self.current_cell = []
            return

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignore_depth:
            self.ignore_depth -= 1
            return

        if self.ignore_depth:
            return

        if tag == "title":
            self.capture_title = False
            return

        if tag == "a" and self.current_link:
            self.current_text.append(f" ({self.current_link})")
            self.current_link = None
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "pre", "li"}:
            self.flush_block()
            return

        if tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self.flush_block()
            return

        if tag in {"th", "td"} and self.current_cell is not None and self.current_row is not None:
            self.current_row.append("".join(self.current_cell).strip())
            self.current_cell = None
            return

        if tag == "tr" and self.current_row:
            self.table_rows.append(self.current_row)
            self.current_row = None
            return

        if tag == "table" and self.table_rows:
            for row in self.table_rows:
                self.output.append(" | ".join(cell for cell in row if cell))
            self.output.append("")
            self.table_rows = []

    def handle_data(self, data: str) -> None:
        if self.ignore_depth:
            return

        if self.capture_title:
            self.title_text.append(data)

        if self.current_cell is not None:
            self.current_cell.append(data)
            return

        self.current_text.append(data)

    def flush_block(self) -> None:
        if not self.current_text:
            self.current_block_tag = None
            return

        raw = "".join(self.current_text).strip()
        self.current_text = []
        tag = self.current_block_tag
        self.current_block_tag = None

        if not raw:
            return

        if tag and tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            level = int(tag[1])
            line = f"{'#' * level} {raw}"
            if level == 1 and not self.first_heading:
                self.first_heading = raw
            self.output.append(line)
        elif tag == "blockquote":
            self.output.append(f"> {raw}")
        elif tag == "pre":
            self.output.extend(["```", raw, "```"])
        else:
            self.output.append(raw)

        self.output.append("")

    def as_markdown(self) -> Tuple[str, str]:
        self.flush_block()
        title = " ".join(part.strip() for part in self.title_text if part.strip()).strip()
        if not title and self.first_heading:
            title = self.first_heading
        return normalize_whitespace("\n".join(self.output)), title


def html_to_markdown(html: str) -> Tuple[str, str]:
    parser = HtmlToMarkdownParser()
    parser.feed(html)
    return parser.as_markdown()


def human_title_from_ref(source_ref: str) -> str:
    stem = Path(urllib.parse.urlparse(source_ref).path or source_ref).stem
    stem = stem.replace("-", " ").replace("_", " ").strip()
    return stem.title() or "Imported Source"


def convert_text_like(data: bytes, extension: str, source_ref: str) -> ConversionResult:
    text = data.decode("utf-8", errors="replace")
    return ConversionResult(
        title=human_title_from_ref(source_ref),
        source_filename=f"source{extension}",
        source_bytes=data,
        content_markdown=normalize_whitespace(text),
        source_type="local-file",
        source_ref=source_ref,
        source_format=extension.lstrip("."),
        conversion_status="converted",
        extraction_confidence="high",
        review_required=False,
        warnings=[],
        asset_paths=[],
        asset_files=[],
    )


def convert_html_bytes(data: bytes, source_ref: str, source_type: str) -> ConversionResult:
    html = data.decode("utf-8", errors="replace")
    markdown, title = html_to_markdown(html)
    return ConversionResult(
        title=title or human_title_from_ref(source_ref),
        source_filename="source.html",
        source_bytes=data,
        content_markdown=markdown,
        source_type=source_type,
        source_ref=source_ref,
        source_format="html",
        conversion_status="converted",
        extraction_confidence="medium",
        review_required=False,
        warnings=[],
        asset_paths=[],
        asset_files=[],
    )


def convert_docx(path: Path, source_ref: str) -> ConversionResult:
    result = subprocess.run(
        ["/usr/bin/textutil", "-convert", "html", str(path), "-stdout"],
        capture_output=True,
        check=True,
    )
    markdown, title = html_to_markdown(result.stdout.decode("utf-8", errors="replace"))
    return ConversionResult(
        title=title or human_title_from_ref(source_ref),
        source_filename="source.docx",
        source_bytes=path.read_bytes(),
        content_markdown=markdown,
        source_type="local-file",
        source_ref=source_ref,
        source_format="docx",
        conversion_status="converted",
        extraction_confidence="medium",
        review_required=False,
        warnings=[],
        asset_paths=[],
        asset_files=[],
    )


def convert_pdf(path: Path, source_ref: str) -> ConversionResult:
    reader = PdfReader(str(path))
    warnings: List[str] = []
    pages: List[str] = []

    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            warnings.append(f"page {index} extracted no text")
            continue
        pages.append(f"## Page {index}\n\n{text}")

    content = "\n\n".join(pages).strip()
    if not content:
        content = "# PDF Import\n\nNo extractable text was found."

    return ConversionResult(
        title=human_title_from_ref(source_ref),
        source_filename="source.pdf",
        source_bytes=path.read_bytes(),
        content_markdown=normalize_whitespace(content),
        source_type="local-file",
        source_ref=source_ref,
        source_format="pdf",
        conversion_status="converted",
        extraction_confidence="medium",
        review_required=bool(warnings),
        warnings=warnings,
        asset_paths=[],
        asset_files=[],
    )


def convert_pptx(path: Path, source_ref: str) -> ConversionResult:
    try:
        extraction = extract_pptx_bundle(path)
    except (BadZipFile, ET.ParseError, KeyError, ValueError) as exc:
        raise ValueError(f"Unsupported or unreadable presentation import: {path}") from exc
    asset_paths = [asset_path for asset_path, _ in extraction.asset_files]
    return ConversionResult(
        title=extraction.title,
        source_filename="source.pptx",
        source_bytes=path.read_bytes(),
        content_markdown=normalize_whitespace(extraction.markdown),
        source_type="local-file",
        source_ref=source_ref,
        source_format="pptx",
        conversion_status="converted",
        extraction_confidence=extraction.extraction_confidence,
        review_required=bool(extraction.warnings),
        warnings=extraction.warnings,
        asset_paths=asset_paths,
        asset_files=extraction.asset_files,
    )


def convert_image(path: Path, source_ref: str) -> ConversionResult:
    try:
        extraction = extract_image_bundle(path)
    except ValueError as exc:
        raise ValueError(f"Unsupported or unreadable image import: {path}") from exc
    asset_paths = [asset_path for asset_path, _ in extraction.asset_files]
    return ConversionResult(
        title=extraction.title,
        source_filename=f"source{path.suffix.lower()}",
        source_bytes=path.read_bytes(),
        content_markdown=normalize_whitespace(extraction.markdown),
        source_type="local-file",
        source_ref=source_ref,
        source_format=path.suffix.lower().lstrip("."),
        conversion_status="converted",
        extraction_confidence=extraction.extraction_confidence,
        review_required=True,
        warnings=extraction.warnings,
        asset_paths=asset_paths,
        asset_files=extraction.asset_files,
    )


def convert_source(source: str) -> ConversionResult:
    kind = detect_source_kind(source)
    data, extension, content_type = read_source_bytes(source)

    if kind == "url":
        if extension == ".html" or content_type == "text/html":
            return convert_html_bytes(data, source, "web-article")
        raise ValueError(f"Unsupported URL import type for source: {source}")

    path = Path(source)

    if extension in {".txt", ".md"}:
        return convert_text_like(data, extension, str(path))
    if extension in {".html", ".htm"}:
        return convert_html_bytes(data, str(path), "local-file")
    if extension == ".docx":
        return convert_docx(path, str(path))
    if extension == ".pdf":
        return convert_pdf(path, str(path))
    multimodal_kind = classify_multimodal_input(path)
    if multimodal_kind is MultimodalInputKind.OFFICE and extension == ".pptx":
        return convert_pptx(path, str(path))
    if multimodal_kind is MultimodalInputKind.IMAGE:
        return convert_image(path, str(path))

    raise ValueError(f"Unsupported source format: {extension or 'unknown'}")


def build_metadata(
    result: ConversionResult,
    bundle_path: Path,
    primary_domain: str,
    related_domains: List[str],
    privacy: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = hashlib.sha256(result.source_bytes).hexdigest()
    related = ", ".join(yaml_quote(domain) for domain in related_domains)
    warnings = ", ".join(yaml_quote(warning) for warning in result.warnings)
    assets = ", ".join(yaml_quote(asset) for asset in result.asset_paths)
    source_refs = f"[{yaml_quote(result.source_ref)}]"

    lines = [
        "---",
        f"id: {bundle_path.name}",
        f"title: {yaml_quote(result.title)}",
        "layer: raw",
        "note_type: raw-bundle",
        f"primary_domain: {primary_domain}",
        f"related_domains: [{related}]" if related else "related_domains: []",
        f"privacy: {privacy}",
        "status: active",
        f"created_at: {now}",
        f"updated_at: {now}",
        f"source_refs: {source_refs}",
        "",
        f"source_format: {result.source_format}",
        f"source_filename: {result.source_filename}",
        f"source_path: {yaml_quote((bundle_path / result.source_filename).as_posix())}",
        f"source_type: {result.source_type}",
        f"source_ref: {yaml_quote(result.source_ref)}",
        f"imported_at: {now}",
        "published_at:",
        f"content_hash: {content_hash}",
        "",
        f"conversion_status: {result.conversion_status}",
        "converter: import_bundle.py",
        f"extraction_confidence: {result.extraction_confidence}",
        f"review_required: {'true' if result.review_required else 'false'}",
        f"warnings: [{warnings}]" if warnings else "warnings: []",
        "",
        f"asset_paths: [{assets}]" if assets else "asset_paths: []",
        "---",
        "",
        "# Raw Bundle Metadata",
        "",
    ]
    return "\n".join(lines)


def import_source(
    root: Path,
    source: str,
    primary_domain: str,
    related_domains: Optional[List[str]] = None,
    privacy: str = "private",
) -> Path:
    related_domains = related_domains or []
    result = convert_source(source)
    bundle_path = ensure_unique_bundle_path(root, slugify(result.title))
    bundle_path.mkdir(parents=True, exist_ok=False)
    (bundle_path / "assets").mkdir()

    (bundle_path / result.source_filename).write_bytes(result.source_bytes)
    (bundle_path / "content.md").write_text(result.content_markdown, encoding="utf-8")
    for asset_path, asset_bytes in result.asset_files:
        target_path = bundle_path / asset_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(asset_bytes)
    (bundle_path / "metadata.md").write_text(
        build_metadata(result, bundle_path, primary_domain, related_domains, privacy),
        encoding="utf-8",
    )

    return bundle_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a source file or URL into an Infinite Lore raw bundle.")
    parser.add_argument("--source", required=True, help="Path or URL to import")
    parser.add_argument("--domain", required=True, help="Primary domain id")
    parser.add_argument("--related-domain", action="append", default=[], help="Related domain id")
    parser.add_argument("--privacy", default="private", help="Privacy tier")
    parser.add_argument("--root", default=".", help="Vault root path")
    parser.add_argument("--skip-compile", action="store_true", help="Only import the raw bundle without compiling")
    args = parser.parse_args()

    root = Path(args.root)
    bundle = import_source(root, args.source, args.domain, args.related_domain, args.privacy)
    if not args.skip_compile:
        try:
            from tools.wiki_compile import compile_bundle
        except ModuleNotFoundError:
            from wiki_compile import compile_bundle

        compile_bundle(root, bundle)
    print(bundle.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
