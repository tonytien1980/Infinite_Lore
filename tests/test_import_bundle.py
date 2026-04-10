import subprocess
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from PIL import Image

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

def write_minimal_pptx(path: Path, slide_title: str = "Slide One") -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>
"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>
"""
    presentation = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId1"/>
  </p:sldIdLst>
</p:presentation>
"""
    presentation_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>
"""
    slide = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:t>{slide_title}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("ppt/presentation.xml", presentation)
        archive.writestr("ppt/_rels/presentation.xml.rels", presentation_rels)
        archive.writestr("ppt/slides/slide1.xml", slide)


def write_test_png(path: Path) -> None:
    image = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    image.save(path, format="PNG")


def write_malformed_pptx(path: Path) -> None:
    path.write_bytes(b"not a valid pptx archive")


def write_malformed_png(path: Path) -> None:
    path.write_bytes(b"not a valid png image")


class ImportBundleTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_imports_text_file_into_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "note.txt"
            source.write_text("Alpha\n\nBeta\n", encoding="utf-8")

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
            txt.write_text("Docx Title\n\nDocx Body\n", encoding="utf-8")
            subprocess.run(
                ["/usr/bin/textutil", "-convert", "docx", str(txt), "-output", str(docx)],
                check=True,
            )

            bundle = import_source(root, str(docx), "consulting")
            content = self.read(bundle / "content.md")

            self.assertTrue((bundle / "source.docx").exists())
            self.assertIn("Docx Title", content)
            self.assertIn("conversion_status: converted", self.read(bundle / "metadata.md"))

    def test_imports_pptx_into_raw_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pptx"
            write_minimal_pptx(source, slide_title="Slide One")

            bundle = import_source(root, str(source), "product-strategy")

            self.assertTrue((bundle / "source.pptx").exists())
            self.assertTrue((bundle / "content.md").exists())
            self.assertTrue((bundle / "metadata.md").exists())
            content = self.read(bundle / "content.md")
            metadata = self.read(bundle / "metadata.md")
            self.assertIn("Slide One", content)
            self.assertIn("source_format: pptx", metadata)
            self.assertIn("conversion_status: converted", metadata)

    def test_imports_uppercase_supported_extensions_into_raw_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pptx_source = root / "DECK.PPTX"
            png_source = root / "PREVIEW.PNG"
            write_minimal_pptx(pptx_source, slide_title="Uppercase Slide")
            write_test_png(png_source)

            pptx_bundle = import_source(root, str(pptx_source), "product-strategy")
            png_bundle = import_source(root, str(png_source), "product-strategy")

            self.assertTrue((pptx_bundle / "source.pptx").exists())
            self.assertIn("Uppercase Slide", self.read(pptx_bundle / "content.md"))
            self.assertIn("source_format: pptx", self.read(pptx_bundle / "metadata.md"))

            self.assertTrue((png_bundle / "source.png").exists())
            self.assertIn("source_format: png", self.read(png_bundle / "metadata.md"))
            self.assertIn("conversion_status: converted", self.read(png_bundle / "metadata.md"))

    def test_imports_png_into_raw_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "diagram.png"
            write_test_png(source)

            bundle = import_source(root, str(source), "product-strategy")

            self.assertTrue((bundle / "source.png").exists())
            self.assertTrue((bundle / "content.md").exists())
            self.assertTrue((bundle / "metadata.md").exists())
            content = self.read(bundle / "content.md")
            metadata = self.read(bundle / "metadata.md")
            self.assertIn("# Image Import", content)
            self.assertIn("## Structural Summary", content)
            self.assertIn("extremely small", content)
            self.assertIn("## Visible Text", content)
            self.assertIn("source_format: png", metadata)
            self.assertIn("conversion_status: converted", metadata)
            self.assertIn("extraction_confidence: low", metadata)
            self.assertIn("review_required: true", metadata)

    def test_imports_pptx_with_no_extractable_text_still_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "review-needed.pptx"
            write_minimal_pptx(source, slide_title="")

            bundle = import_source(root, str(source), "product-strategy")
            content = self.read(bundle / "content.md")
            metadata = self.read(bundle / "metadata.md")

            self.assertIn("No extractable slide text was found.", content)
            self.assertIn("conversion_status: converted", metadata)
            self.assertIn("extraction_confidence: low", metadata)
            self.assertIn("review_required: true", metadata)
            self.assertIn("slide 1 extracted no text", metadata)

    def test_malformed_pptx_fails_with_controlled_import_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "broken.pptx"
            write_malformed_pptx(source)

            with self.assertRaises(ValueError):
                import_source(root, str(source), "product-strategy")

    def test_malformed_image_fails_with_controlled_import_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "broken.png"
            write_malformed_png(source)

            with self.assertRaises(ValueError):
                import_source(root, str(source), "product-strategy")

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
