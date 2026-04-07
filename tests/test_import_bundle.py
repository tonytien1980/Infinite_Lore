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
