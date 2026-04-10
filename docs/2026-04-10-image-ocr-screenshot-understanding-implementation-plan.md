# Image OCR And Screenshot Understanding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dependable local OCR on this Mac plus bounded screenshot-aware image normalization to the existing raw bundle pipeline.

**Architecture:** Introduce a small local Apple Vision OCR helper and a Python wrapper, then upgrade `tools/image_adapter.py` to prefer that OCR path and emit richer image markdown plus explicit metadata fields. Keep the existing `source.* -> content.md -> metadata.md -> assets/` bundle contract, and only borrow `Graphify` patterns for stage separation and file-type posture rather than pretending it already ships a reusable OCR engine.

**Tech Stack:** Python 3.9, Swift 6, Apple Vision `VNRecognizeTextRequest`, existing `tools/import_bundle.py`, existing raw bundle writer, Pillow, unittest

---

## File Structure

- Create: `tools/vision_ocr.swift`
  - small local Swift helper that runs Vision OCR and prints structured JSON
- Create: `tools/vision_ocr.py`
  - Python wrapper around the Swift helper with normalized result parsing
- Modify: `tools/image_adapter.py`
  - prefer Vision OCR, build OCR-aware markdown, and emit image-specific metadata signals
- Modify: `tools/import_bundle.py`
  - pass image-specific metadata through the existing raw bundle writer without breaking other formats
- Create: `tests/test_vision_ocr.py`
  - wrapper-level unit tests with mocked subprocess output
- Create: `tests/test_image_adapter.py`
  - image-adapter formatting, fallback, and screenshot-signal tests
- Modify: `tests/test_import_bundle.py`
  - end-to-end raw bundle assertions for image OCR metadata and fallback behavior
- Modify after implementation: `00_System/Workflow Guide.md`
  - describe the new local OCR behavior and fallback posture
- Modify after implementation: `docs/2026-04-08-execution-roadmap.md`
  - mark Phase 10 delivered and update the verified baseline
- Modify after implementation: `docs/2026-04-10-image-ocr-screenshot-understanding-spec.md`
  - update status from review draft to delivered behavior

This keeps the OCR engine boundary isolated while preserving the importer contract and minimizing risk to non-image formats.

## Task 1: Lock Red Tests For Local Vision OCR

**Files:**
- Create: `tests/test_vision_ocr.py`

- [ ] **Step 1: Write the failing wrapper tests**

```python
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.vision_ocr import VisionOcrResult, run_vision_ocr


class VisionOcrTests(unittest.TestCase):
    def test_run_vision_ocr_parses_success_payload(self) -> None:
        payload = json.dumps(
            {
                "engine": "apple-vision",
                "status": "success",
                "text": "Hello World",
                "lines": ["Hello World"],
                "line_count": 1,
                "region_count": 1,
            }
        )
        completed = subprocess.CompletedProcess(
            args=["swift"],
            returncode=0,
            stdout=payload,
            stderr="",
        )

        with patch("subprocess.run", return_value=completed):
            result = run_vision_ocr(Path("/tmp/sample.png"))

        self.assertEqual(result.engine, "apple-vision")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.text, "Hello World")
        self.assertEqual(result.line_count, 1)

    def test_run_vision_ocr_returns_unavailable_when_swift_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            result = run_vision_ocr(Path("/tmp/sample.png"))

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.text, "")
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_vision_ocr -v
```

Expected:

- FAIL because `tools/vision_ocr.py` does not exist yet

- [ ] **Step 3: Commit the red test coverage**

```bash
git add tests/test_vision_ocr.py
git commit -m "test: add vision ocr wrapper coverage"
```

## Task 2: Implement The Local Vision OCR Helper And Python Wrapper

**Files:**
- Create: `tools/vision_ocr.swift`
- Create: `tools/vision_ocr.py`
- Test: `tests/test_vision_ocr.py`

- [ ] **Step 1: Implement the Swift helper output contract**

Use a stable JSON payload shape like:

```swift
import Foundation
import Vision
import AppKit

struct OCRPayload: Codable {
    let engine: String
    let status: String
    let text: String
    let lines: [String]
    let lineCount: Int
    let regionCount: Int
    let warning: String?
}
```

The helper should:

- read one image path from CLI args
- run `VNRecognizeTextRequest`
- sort recognized observations into reading order
- print JSON to stdout

- [ ] **Step 2: Implement the Python wrapper and normalized result object**

Use a minimal wrapper like:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class VisionOcrResult:
    engine: str
    status: str
    text: str
    lines: List[str]
    line_count: int
    region_count: int
    warning: str = ""


def run_vision_ocr(path: Path) -> VisionOcrResult:
    swift = shutil.which("swift")
    if not swift:
        return VisionOcrResult("apple-vision", "unavailable", "", [], 0, 0, "swift not installed")
    helper = Path(__file__).with_name("vision_ocr.swift")
    completed = subprocess.run(
        [swift, str(helper), str(path)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return VisionOcrResult("apple-vision", "failed", "", [], 0, 0, completed.stderr.strip())
    payload = json.loads(completed.stdout)
    return VisionOcrResult(
        payload["engine"],
        payload["status"],
        payload["text"],
        payload["lines"],
        payload["line_count"],
        payload["region_count"],
        payload.get("warning", ""),
    )
```

The wrapper should:

- detect whether `swift` is available
- run `swift tools/vision_ocr.swift <image-path>`
- parse JSON robustly
- normalize failure modes into bounded statuses such as:
  - `success`
  - `no-text`
  - `unavailable`
  - `failed`

- [ ] **Step 3: Re-run the targeted tests**

Run:

```bash
python3 -m unittest tests.test_vision_ocr -v
```

Expected:

- PASS

- [ ] **Step 4: Commit**

```bash
git add tools/vision_ocr.swift tools/vision_ocr.py tests/test_vision_ocr.py
git commit -m "feat: add local vision ocr helper"
```

## Task 3: Add Red Tests For OCR-Aware Image Normalization

**Files:**
- Create: `tests/test_image_adapter.py`
- Modify: `tests/test_import_bundle.py`

- [ ] **Step 1: Write failing image-adapter tests**

Cover:

- successful OCR adds:
  - `## OCR Summary`
  - `## OCR Text`
  - `## Screenshot Signals`
- fallback without OCR still keeps the current bounded image summary posture
- screenshot signals stay bounded and conservative

Use a mocked OCR result like:

```python
from pathlib import Path
from unittest.mock import patch

from tools.image_adapter import extract_image_bundle
from tools.vision_ocr import VisionOcrResult


@patch(
    "tools.image_adapter.run_vision_ocr",
    return_value=VisionOcrResult(
        engine="apple-vision",
        status="success",
        text="Quarterly revenue grew 12 percent",
        lines=["Quarterly revenue grew 12 percent"],
        line_count=1,
        region_count=1,
        warning="",
    ),
)
def test_extract_image_bundle_uses_ocr_sections(self, _mock_ocr) -> None:
    result = extract_image_bundle(self.sample_png)
    self.assertIn("## OCR Summary", result.markdown)
    self.assertIn("## OCR Text", result.markdown)
    self.assertIn("Quarterly revenue grew 12 percent", result.markdown)
```

- [ ] **Step 2: Write failing raw-bundle metadata tests**

Extend `tests/test_import_bundle.py` to assert image bundles now emit:

- `ocr_engine`
- `ocr_attempted`
- `ocr_status`
- `ocr_text_present`
- `image_interpretation_mode`
- `image_kind_guess`

Example assertion block:

```python
metadata = self.read(bundle / "metadata.md")
self.assertIn("ocr_engine: apple-vision", metadata)
self.assertIn("ocr_attempted: true", metadata)
self.assertIn("ocr_status: success", metadata)
self.assertIn("image_interpretation_mode: bounded-screenshot-signals", metadata)
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_image_adapter tests.test_import_bundle -v
```

Expected:

- FAIL because the current image adapter does not emit OCR-aware sections or extra metadata

- [ ] **Step 4: Commit the red test coverage**

```bash
git add tests/test_image_adapter.py tests/test_import_bundle.py
git commit -m "test: add image ocr normalization coverage"
```

## Task 4: Upgrade The Image Adapter And Metadata Plumbing

**Files:**
- Modify: `tools/image_adapter.py`
- Modify: `tools/import_bundle.py`
- Test: `tests/test_image_adapter.py`
- Test: `tests/test_import_bundle.py`

- [ ] **Step 1: Extend the image extraction contract**

Update `ImageExtractionResult` so it can carry OCR and interpretation metadata explicitly.

Use fields like:

```python
@dataclass
class ImageExtractionResult:
    title: str
    markdown: str
    warnings: List[str]
    extraction_confidence: str
    asset_files: List[Tuple[str, bytes]]
    review_required: bool
    ocr_engine: str
    ocr_attempted: bool
    ocr_status: str
    ocr_text_present: bool
    image_interpretation_mode: str
    image_kind_guess: str
```

- [ ] **Step 2: Replace `_extract_visible_text()` with Vision-first OCR**

Use the wrapper rather than direct `tesseract` probing:

```python
from tools.vision_ocr import VisionOcrResult, run_vision_ocr


def _extract_local_ocr(path: Path) -> VisionOcrResult:
    return run_vision_ocr(path)
```

On fallback:

- preserve the structural summary path
- add a warning about OCR unavailability or failure
- keep `review_required: true`

- [ ] **Step 3: Add bounded screenshot signals and richer markdown sections**

Build normalized output like:

```python
markdown = "\n".join(
    [
        "# Image Import",
        "",
        "## Source Summary",
        f"- Filename: `{path.name}`",
        f"- Format: `{image_format}`",
        f"- Dimensions: `{width} x {height}` pixels",
        "## OCR Summary",
        f"- OCR engine: `{ocr_result.engine}`",
        f"- OCR status: `{ocr_result.status}`",
        f"- Recognized lines: `{ocr_result.line_count}`",
        "## OCR Text",
        visible_text_or_note,
        "",
        "## Screenshot Signals",
        screenshot_signal_text,
        "",
        "## Extraction Notes",
        "This image import uses bounded screenshot-aware normalization.",
        "Review the original image directly if exact layout meaning matters.",
    ]
)
```

Keep screenshot interpretation conservative:

- `ui-like`
- `document-like`
- `mixed`
- `generic-image`

Do not invent stronger semantic claims.

- [ ] **Step 4: Plumb image-specific metadata through the bundle writer**

Add a generic metadata extension field to `ConversionResult`, for example:

```python
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
    extra_metadata: List[Tuple[str, str]]
```

Then populate it in `convert_image()`:

```python
extra_metadata = [
    ("ocr_engine", extraction.ocr_engine),
    ("ocr_attempted", "true" if extraction.ocr_attempted else "false"),
    ("ocr_status", extraction.ocr_status),
    ("ocr_text_present", "true" if extraction.ocr_text_present else "false"),
    ("image_interpretation_mode", extraction.image_interpretation_mode),
    ("image_kind_guess", extraction.image_kind_guess),
]
```

and render it inside `build_metadata()` before the closing frontmatter fence.

- [ ] **Step 5: Re-run the targeted suites**

Run:

```bash
python3 -m unittest tests.test_vision_ocr tests.test_image_adapter tests.test_import_bundle -v
```

Expected:

- PASS
- existing non-image import coverage remains green

- [ ] **Step 6: Commit**

```bash
git add tools/image_adapter.py tools/import_bundle.py tests/test_image_adapter.py tests/test_import_bundle.py
git commit -m "feat: deepen image ocr import support"
```

## Task 5: Sync Docs And Run Full Verification

**Files:**
- Modify: `00_System/Workflow Guide.md`
- Modify: `docs/2026-04-08-execution-roadmap.md`
- Modify: `docs/2026-04-10-image-ocr-screenshot-understanding-spec.md`

- [ ] **Step 1: Update the docs to match shipped behavior**

Document:

- Apple Vision as the primary local OCR path on macOS
- fallback behavior when Vision OCR is unavailable or fails
- the new OCR-aware image `content.md` sections
- the new metadata fields added to image raw bundles

- [ ] **Step 2: Run the focused regression suites**

Run:

```bash
python3 -m unittest tests.test_vision_ocr tests.test_image_adapter tests.test_import_bundle tests.test_multimodal_detect tests.test_wiki_compile tests.test_query_ask -v
```

Expected:

- PASS

- [ ] **Step 3: Run the repo health check**

Run:

```bash
python3 tools/health_check.py .
```

Expected:

- `Vault health check passed`

- [ ] **Step 4: Commit**

```bash
git add 00_System/Workflow\ Guide.md docs/2026-04-08-execution-roadmap.md docs/2026-04-10-image-ocr-screenshot-understanding-spec.md
git commit -m "docs: sync image ocr rollout"
```

## Self-Review

### Spec coverage

- local macOS Vision OCR: covered by Tasks 1 and 2
- OCR-aware image normalization: covered by Tasks 3 and 4
- bounded screenshot understanding signals: covered by Task 4
- explicit image metadata additions: covered by Task 4
- docs and verification: covered by Task 5

### Placeholder scan

- no `TODO`
- no `TBD`
- no “handle appropriately” style placeholders remain

### Type consistency

- `VisionOcrResult` fields are introduced in Task 2 and consumed consistently in Tasks 3 and 4
- `ImageExtractionResult` metadata fields are introduced in Task 4 and consumed in `convert_image()` and `build_metadata()`
- `extra_metadata` is defined before the plan uses it in the bundle writer
