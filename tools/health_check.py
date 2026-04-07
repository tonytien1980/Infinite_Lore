from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List


FORMAL_LAYER_PREFIXES = (
    "10_Domains/",
    "30_Wiki/",
    "40_Projects/",
    "50_Brainstorming/",
    "60_Journal/",
    "70_Artifacts/",
)

SOURCE_REF_REQUIRED_PREFIXES = (
    "30_Wiki/",
    "70_Artifacts/",
)


def parse_frontmatter(text: str) -> Dict[str, object]:
    if not text.startswith("---\n"):
        return {}

    lines = text.splitlines()
    data: Dict[str, object] = {}
    key = None
    in_list = False

    for line in lines[1:]:
        if line.strip() == "---":
            break

        if line.startswith("  - ") and key and in_list:
            data.setdefault(key, [])
            data[key].append(line[4:].strip())
            continue

        if ":" not in line:
            continue

        raw_key, raw_value = line.split(":", 1)
        key = raw_key.strip()
        value = raw_value.strip()

        if value == "[]":
            data[key] = []
            in_list = False
        elif value == "":
            data[key] = []
            in_list = True
        else:
            data[key] = value
            in_list = False

    return data


def should_check_formal_note(relative_path: str) -> bool:
    return relative_path.endswith(".md") and relative_path.startswith(FORMAL_LAYER_PREFIXES)


def check_note(relative_path: str, metadata: Dict[str, object]) -> List[str]:
    errors: List[str] = []

    if "primary_domain" not in metadata or metadata.get("primary_domain") in ("", []):
        errors.append(f"{relative_path}: missing primary_domain")

    if relative_path.startswith(SOURCE_REF_REQUIRED_PREFIXES):
        source_refs = metadata.get("source_refs", [])
        if not source_refs:
            errors.append(f"{relative_path}: missing source_refs")

    if relative_path.startswith("40_Projects/clients/"):
        privacy = metadata.get("privacy")
        if privacy != "client-confidential":
            errors.append(f"{relative_path}: client path must use privacy client-confidential")

    return errors


def check_vault(root: Path) -> Dict[str, List[str]]:
    errors: List[str] = []

    for path in sorted(root.rglob("*.md")):
        relative_path = path.relative_to(root).as_posix()
        if not should_check_formal_note(relative_path):
            continue

        metadata = parse_frontmatter(path.read_text(encoding="utf-8"))
        errors.extend(check_note(relative_path, metadata))

    return {"errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Infinite Lore vault health.")
    parser.add_argument("root", nargs="?", default=".", help="Vault root path")
    args = parser.parse_args()

    report = check_vault(Path(args.root))
    if report["errors"]:
        for error in report["errors"]:
            print(error)
        return 1

    print("Vault health check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
