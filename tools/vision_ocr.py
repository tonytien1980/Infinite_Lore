from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

_ALLOWED_STATUSES = {"success", "no-text", "unavailable", "failed"}


@dataclass
class VisionOcrResult:
    engine: str
    status: str
    text: str
    lines: List[str]
    line_count: int
    region_count: int
    warning: str


def _normalize_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status in _ALLOWED_STATUSES:
        return status
    if status in {"ok", "complete"}:
        return "success"
    if status in {"empty", "not-found", "no_text"}:
        return "no-text"
    if status in {"missing", "unsupported"}:
        return "unavailable"
    return "failed"


def _coerce_lines(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _extract_json_object(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ValueError("missing JSON output")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("missing JSON object")
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("JSON payload must be an object")
    return parsed


def _result_from_payload(payload: Dict[str, Any]) -> VisionOcrResult:
    lines = _coerce_lines(payload.get("lines"))
    text = str(payload.get("text") or "").strip()
    if not text and lines:
        text = "\n".join(lines)

    line_count = payload.get("line_count")
    if not isinstance(line_count, int):
        line_count = len(lines)

    region_count = payload.get("region_count")
    if not isinstance(region_count, int):
        region_count = line_count

    return VisionOcrResult(
        engine=str(payload.get("engine") or "apple-vision"),
        status=_normalize_status(payload.get("status")),
        text=text,
        lines=lines,
        line_count=max(0, line_count),
        region_count=max(0, region_count),
        warning=str(payload.get("warning") or "").strip(),
    )


def run_vision_ocr(path: Path) -> VisionOcrResult:
    swift = shutil.which("swift")
    if not swift:
        return VisionOcrResult(
            engine="apple-vision",
            status="unavailable",
            text="",
            lines=[],
            line_count=0,
            region_count=0,
            warning="swift runtime unavailable",
        )

    script_path = Path(__file__).with_name("vision_ocr.swift")

    try:
        completed = subprocess.run(
            [swift, str(script_path), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return VisionOcrResult(
            engine="apple-vision",
            status="unavailable",
            text="",
            lines=[],
            line_count=0,
            region_count=0,
            warning=str(exc),
        )

    try:
        payload = _extract_json_object(completed.stdout)
    except (ValueError, json.JSONDecodeError):
        warning = completed.stderr.strip() or "vision OCR returned invalid JSON"
        return VisionOcrResult(
            engine="apple-vision",
            status="failed",
            text="",
            lines=[],
            line_count=0,
            region_count=0,
            warning=warning,
        )

    result = _result_from_payload(payload)
    if result.status == "failed" and not result.warning:
        result.warning = completed.stderr.strip()
    return result
