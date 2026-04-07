# Multi-Format Import Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first usable multi-format import pipeline that converts `txt`, `md`, `html`, web article URLs, `docx`, and `pdf` inputs into raw bundle folders with `source.*`, `content.md`, and `metadata.md`.

**Architecture:** The implementation uses one Python entrypoint with shared bundle-writing and normalization logic plus format-specific adapters. It relies on Python standard library, `pypdf` for PDF text extraction, and macOS `textutil` for DOCX-to-HTML conversion so the resulting bundle contract stays consistent across formats.

**Tech Stack:** Python 3.9 standard library, `unittest`, `pypdf`, macOS `textutil`, Markdown, YAML frontmatter

---

## File Structure

### Files to create

- `docs/2026-04-07-multi-format-import-pipeline-implementation-plan.md`
- `tools/import_bundle.py`
- `tests/test_import_bundle.py`
- `requirements.txt`

### Files to modify

- `00_System/Template - Raw Metadata.md`
- `00_System/Workflow Guide.md`

## Task 1: Align Raw Metadata Template And Setup Notes

**Files:**

- Modify: `00_System/Template - Raw Metadata.md`
- Modify: `00_System/Workflow Guide.md`
- Create: `requirements.txt`

- [ ] **Step 1: Expand the raw metadata template to match the bundle contract**

Replace the contents of `00_System/Template - Raw Metadata.md` with:

```md
---
id:
title:
layer: raw
note_type: raw-bundle
primary_domain:
related_domains: []
privacy:
status:
created_at:
updated_at:
source_refs: []

source_format:
source_filename:
source_path:
source_type:
source_ref:
imported_at:
published_at:
content_hash:

conversion_status:
converter:
extraction_confidence:
review_required:
warnings: []

asset_paths: []
---

# Raw Bundle Metadata
```

- [ ] **Step 2: Add the importer command to the workflow guide**

Append this section to `00_System/Workflow Guide.md`:

```md
## Raw Import

Use the importer to normalize new source material into raw bundles:

```bash
python3 tools/import_bundle.py --source <path-or-url> --domain <primary-domain>
```

This creates a bundle in `20_Raw/inbox/` containing the original source, `content.md`, and `metadata.md`.
```

- [ ] **Step 3: Declare the Python dependency used by the importer**

Create `requirements.txt` with:

```txt
pypdf>=6.9,<7
```

- [ ] **Step 4: Verify the documentation and dependency files are in place**

Run:

```bash
rg --files 00_System requirements.txt
```

Expected:

- output includes the updated raw metadata template
- output includes the workflow guide
- output includes `requirements.txt`

## Task 2: Write Failing Importer Tests

**Files:**

- Create: `tests/test_import_bundle.py`

- [ ] **Step 1: Write tests for text, HTML, URL, DOCX, and PDF imports**

Create `tests/test_import_bundle.py` with:

```python
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.import_bundle import import_source


PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 18 Tf
72 72 Td
(Hello PDF World) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000241 00000 n
0000000335 00000 n
trailer
<< /Root 1 0 R /Size 6 >>
startxref
405
%%EOF
"""


class ImportBundleTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_imports_text_file_into_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "note.txt"
            source.write_text("Alpha\\n\\nBeta\\n", encoding="utf-8")

            bundle = import_source(root, str(source), "ai-application")

            self.assertTrue((bundle / "source.txt").exists())
            self.assertIn("Alpha", self.read(bundle / "content.md"))
            self.assertIn("source_format: txt", self.read(bundle / "metadata.md"))
            self.assertIn("conversion_status: converted", self.read(bundle / "metadata.md"))

    def test_imports_html_file_as_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "page.html"
            source.write_text(
                textwrap.dedent(
                    """
                    <html>
                      <head><title>Sample Page</title></head>
                      <body>
                        <h1>Main Title</h1>
                        <p>First paragraph.</p>
                        <ul><li>One</li><li>Two</li></ul>
                      </body>
                    </html>
                    """
                ),
                encoding="utf-8",
            )

            bundle = import_source(root, str(source), "business-strategy")
            content = self.read(bundle / "content.md")

            self.assertIn("# Main Title", content)
            self.assertIn("First paragraph.", content)
            self.assertIn("- One", content)

    def test_imports_file_url_as_web_article(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "article.html"
            source.write_text(
                "<html><head><title>URL Article</title></head><body><article><h1>URL Article</h1><p>Body text.</p></article></body></html>",
                encoding="utf-8",
            )

            bundle = import_source(root, source.as_uri(), "management")

            self.assertTrue((bundle / "source.html").exists())
            self.assertIn("URL Article", self.read(bundle / "content.md"))
            self.assertIn("source_type: web-article", self.read(bundle / "metadata.md"))

    def test_imports_docx_via_textutil(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            txt = root / "source.txt"
            docx = root / "source.docx"
            txt.write_text("Docx Title\\n\\nDocx Body\\n", encoding="utf-8")
            subprocess.run(
                ["/usr/bin/textutil", "-convert", "docx", str(txt), "-output", str(docx)],
                check=True,
            )

            bundle = import_source(root, str(docx), "consulting")
            content = self.read(bundle / "content.md")

            self.assertTrue((bundle / "source.docx").exists())
            self.assertIn("Docx Title", content)
            self.assertIn("conversion_status: converted", self.read(bundle / "metadata.md"))

    def test_imports_pdf_via_pypdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "sample.pdf"
            pdf.write_bytes(PDF_BYTES)

            bundle = import_source(root, str(pdf), "finance-investing")
            content = self.read(bundle / "content.md")
            metadata = self.read(bundle / "metadata.md")

            self.assertTrue((bundle / "source.pdf").exists())
            self.assertIn("Hello PDF World", content)
            self.assertIn("source_format: pdf", metadata)
            self.assertIn("extraction_confidence: medium", metadata)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_import_bundle -v
```

Expected:

- failure because `tools.import_bundle` does not exist yet

## Task 3: Implement The Importer Foundation

**Files:**

- Create: `tools/import_bundle.py`

- [ ] **Step 1: Create the importer module with shared helpers and adapters**

Create `tools/import_bundle.py` with:

```python
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional

from pypdf import PdfReader


VAULT_INBOX = Path("20_Raw/inbox")


@dataclass
class ConversionResult:
    title: str
    source_filename: str
    source_extension: str
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


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "import"


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
    if parsed.scheme in ("http", "https", "file"):
        return "url"
    return "path"


def read_source_bytes(source: str) -> tuple[bytes, str, str]:
    kind = detect_source_kind(source)
    if kind == "url":
        with urllib.request.urlopen(source) as response:
            data = response.read()
            content_type = response.headers.get_content_type()
            path = urllib.parse.urlparse(source).path
            ext = Path(path).suffix.lower()
            if not ext and content_type == "text/html":
                ext = ".html"
            return data, ext or ".bin", content_type

    path = Path(source)
    return path.read_bytes(), path.suffix.lower(), ""


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    collapsed: List[str] = []
    blank_count = 0
    for line in lines:
        if line.strip():
            blank_count = 0
            collapsed.append(line)
        else:
            blank_count += 1
            if blank_count <= 2:
                collapsed.append("")
    return "\n".join(collapsed).strip() + "\n"


class HtmlToMarkdownParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.output: List[str] = []
        self.current: List[str] = []
        self.list_stack: List[str] = []
        self.ignore_stack: List[str] = []
        self.title_text: List[str] = []
        self.capture_title = False
        self.current_link: Optional[str] = None
        self.table_rows: List[List[str]] = []
        self.current_row: List[str] = []
        self.current_cell: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style"}:
            self.ignore_stack.append(tag)
            return
        if self.ignore_stack:
            return
        if tag == "title":
            self.capture_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "pre"}:
            self.flush_current()
            self.current.append(f"__BLOCK__:{tag}")
        elif tag in {"ul", "ol"}:
            self.list_stack.append(tag)
        elif tag == "li":
            self.flush_current()
            marker = "- " if not self.list_stack or self.list_stack[-1] == "ul" else "1. "
            self.current.append(marker)
        elif tag == "br":
            self.current.append("\n")
        elif tag == "a":
            for key, value in attrs:
                if key == "href":
                    self.current_link = value
                    break
        elif tag == "tr":
            self.current_row = []
        elif tag in {"th", "td"}:
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self.ignore_stack and tag == self.ignore_stack[-1]:
            self.ignore_stack.pop()
            return
        if self.ignore_stack:
            return
        if tag == "title":
            self.capture_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "pre", "li"}:
            self.flush_current()
        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self.flush_current()
        elif tag == "a" and self.current_link:
            self.current.append(f" ({self.current_link})")
            self.current_link = None
        elif tag in {"th", "td"}:
            self.current_row.append("".join(self.current_cell).strip())
            self.current_cell = []
        elif tag == "tr":
            if self.current_row:
                self.table_rows.append(self.current_row)
            self.current_row = []
        elif tag == "table":
            if self.table_rows:
                for row in self.table_rows:
                    self.output.append(" | ".join(cell for cell in row if cell))
                self.output.append("")
            self.table_rows = []

    def handle_data(self, data: str) -> None:
        if self.ignore_stack:
            return
        if self.capture_title:
            self.title_text.append(data)
        if self.current_cell != []:
            self.current_cell.append(data)
        else:
            self.current.append(data)

    def flush_current(self) -> None:
        if not self.current:
            return
        raw = "".join(self.current).strip()
        self.current = []
        if not raw:
            return
        block = None
        if raw.startswith("__BLOCK__:"):
            block, _, raw = raw.partition("\n")
            tag = block.replace("__BLOCK__:", "", 1)
            raw = raw.strip()
            if not raw:
                return
            if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
                self.output.append(f"{'#' * int(tag[1])} {raw}")
            elif tag == "blockquote":
                self.output.append(f"> {raw}")
            elif tag == "pre":
                self.output.append("```")
                self.output.append(raw)
                self.output.append("```")
            else:
                self.output.append(raw)
        else:
            self.output.append(raw)
        self.output.append("")

    def as_markdown(self) -> tuple[str, str]:
        self.flush_current()
        title = " ".join(part.strip() for part in self.title_text if part.strip()).strip()
        return normalize_whitespace("\n".join(self.output)), title


def html_to_markdown(html: str) -> tuple[str, str]:
    parser = HtmlToMarkdownParser()
    parser.feed(html)
    return parser.as_markdown()


def convert_text_like(data: bytes, extension: str, source_ref: str) -> ConversionResult:
    text = data.decode("utf-8", errors="replace")
    title = Path(source_ref).stem.replace("-", " ").replace("_", " ").strip() or "Imported Text"
    return ConversionResult(
        title=title.title(),
        source_filename=f"source{extension}",
        source_extension=extension,
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
    )


def convert_html_bytes(data: bytes, extension: str, source_ref: str, source_type: str) -> ConversionResult:
    html = data.decode("utf-8", errors="replace")
    markdown, title = html_to_markdown(html)
    title = title or Path(urllib.parse.urlparse(source_ref).path or source_ref).stem or "Imported HTML"
    return ConversionResult(
        title=title.replace("-", " ").replace("_", " ").strip().title(),
        source_filename=f"source{extension or '.html'}",
        source_extension=extension or ".html",
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
    )


def convert_docx(path: Path, source_ref: str) -> ConversionResult:
    result = subprocess.run(
        ["/usr/bin/textutil", "-convert", "html", str(path), "-stdout"],
        check=True,
        capture_output=True,
    )
    html = result.stdout.decode("utf-8", errors="replace")
    markdown, title = html_to_markdown(html)
    return ConversionResult(
        title=title or path.stem.replace("-", " ").replace("_", " ").title(),
        source_filename="source.docx",
        source_extension=".docx",
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
    )


def convert_pdf(path: Path, source_ref: str) -> ConversionResult:
    reader = PdfReader(str(path))
    pages: List[str] = []
    warnings: List[str] = []
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
        title=path.stem.replace("-", " ").replace("_", " ").title(),
        source_filename="source.pdf",
        source_extension=".pdf",
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
    )


def convert_source(source: str) -> ConversionResult:
    kind = detect_source_kind(source)
    data, extension, content_type = read_source_bytes(source)

    if kind == "url":
        if extension == ".html" or content_type == "text/html":
            return convert_html_bytes(data, ".html", source, "web-article")
        raise ValueError(f"Unsupported URL import type for source: {source}")

    path = Path(source)

    if extension in {".txt", ".md"}:
        return convert_text_like(data, extension, str(path))
    if extension in {".html", ".htm"}:
        return convert_html_bytes(data, ".html", str(path), "local-file")
    if extension == ".docx":
        return convert_docx(path, str(path))
    if extension == ".pdf":
        return convert_pdf(path, str(path))
    if extension == ".pptx":
        raise ValueError("PPTX import is reserved for a later implementation phase")
    if extension in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Image OCR import is reserved for a later implementation phase")

    raise ValueError(f"Unsupported source format: {extension or 'unknown'}")


def render_metadata(result: ConversionResult, bundle_path: Path, primary_domain: str, related_domains: List[str], privacy: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = hashlib.sha256(result.source_bytes).hexdigest()
    related = ", ".join(f'"{domain}"' for domain in related_domains)
    warnings = ", ".join(f'"{warning}"' for warning in result.warnings)
    assets = ", ".join(f'"{asset}"' for asset in result.asset_paths)
    source_refs = f'["{result.source_ref}"]'
    related_block = f"[{related}]" if related else "[]"
    warnings_block = f"[{warnings}]" if warnings else "[]"
    assets_block = f"[{assets}]" if assets else "[]"
    return (
        "---\n"
        f"id: {bundle_path.name}\n"
        f"title: {result.title}\n"
        "layer: raw\n"
        "note_type: raw-bundle\n"
        f"primary_domain: {primary_domain}\n"
        f"related_domains: {related_block}\n"
        f"privacy: {privacy}\n"
        "status: active\n"
        f"created_at: {now}\n"
        f"updated_at: {now}\n"
        f"source_refs: {source_refs}\n\n"
        f"source_format: {result.source_format}\n"
        f"source_filename: {result.source_filename}\n"
        f"source_path: {bundle_path.as_posix()}/{result.source_filename}\n"
        f"source_type: {result.source_type}\n"
        f"source_ref: {result.source_ref}\n"
        f"imported_at: {now}\n"
        "published_at:\n"
        f"content_hash: {content_hash}\n\n"
        f"conversion_status: {result.conversion_status}\n"
        "converter: import_bundle.py\n"
        f"extraction_confidence: {result.extraction_confidence}\n"
        f"review_required: {'true' if result.review_required else 'false'}\n"
        f"warnings: {warnings_block}\n\n"
        f"asset_paths: {assets_block}\n"
        "---\n\n"
        "# Raw Bundle Metadata\n"
    )


def import_source(root: Path, source: str, primary_domain: str, related_domains: Optional[List[str]] = None, privacy: str = "private") -> Path:
    related_domains = related_domains or []
    result = convert_source(source)
    slug = slugify(result.title or "import")
    bundle_path = ensure_unique_bundle_path(root, slug)
    bundle_path.mkdir(parents=True, exist_ok=False)
    (bundle_path / "assets").mkdir()

    (bundle_path / result.source_filename).write_bytes(result.source_bytes)
    (bundle_path / "content.md").write_text(result.content_markdown, encoding="utf-8")
    (bundle_path / "metadata.md").write_text(
        render_metadata(result, bundle_path, primary_domain, related_domains, privacy),
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
    args = parser.parse_args()

    bundle = import_source(Path(args.root), args.source, args.domain, args.related_domain, args.privacy)
    print(bundle.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the importer tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_import_bundle -v
```

Expected:

- all 5 tests pass

## Task 4: Verify The CLI Against Real Project Files

**Files:**

- Modify: `tools/import_bundle.py` only if real-run verification reveals issues

- [ ] **Step 1: Create a small real text source fixture inside the repo**

Run:

```bash
mkdir -p tmp/manual-import && cat > tmp/manual-import/sample.txt <<'EOF'
Infinite Lore is a personal context system.

It should turn raw material into reusable knowledge.
EOF
```

- [ ] **Step 2: Run the importer CLI on the real fixture**

Run:

```bash
python3 tools/import_bundle.py --source tmp/manual-import/sample.txt --domain ai-application --root .
```

Expected:

- command prints a new bundle path under `20_Raw/inbox/`

- [ ] **Step 3: Verify the created bundle contains all required files**

Run:

```bash
find 20_Raw/inbox -maxdepth 2 -type f | sort
```

Expected:

- output includes a new bundle containing `source.txt`, `content.md`, and `metadata.md`

## Task 5: Final Verification

**Files:**

- Verify all files changed in this plan

- [ ] **Step 1: Run all importer-related tests**

Run:

```bash
python3 -m unittest tests.test_import_bundle tests.test_health_check -v
```

Expected:

- all tests pass

- [ ] **Step 2: Run health check on the real vault**

Run:

```bash
python3 tools/health_check.py .
```

Expected:

- `Vault health check passed`

- [ ] **Step 3: Verify the working tree changes are exactly the importer implementation**

Run:

```bash
git status --short
```

Expected:

- modified files match the importer scope
