from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional, Union


class MultimodalInputKind(str, Enum):
    OFFICE = "office"
    IMAGE = "image"


OFFICE_INPUT_EXTENSIONS = {".pptx"}
IMAGE_INPUT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def classify_multimodal_input(source: Union[str, Path]) -> Optional[MultimodalInputKind]:
    suffix = Path(source).suffix.lower()
    if suffix in OFFICE_INPUT_EXTENSIONS:
        return MultimodalInputKind.OFFICE
    if suffix in IMAGE_INPUT_EXTENSIONS:
        return MultimodalInputKind.IMAGE
    return None
