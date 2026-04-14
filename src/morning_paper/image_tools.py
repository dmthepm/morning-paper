from __future__ import annotations

from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageOps


def load_image(source: str) -> Image.Image:
    if source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    normalized = source[7:] if source.startswith("file://") else source
    return Image.open(Path(normalized).expanduser())


def process_for_print(
    source: str,
    *,
    output_path: Path,
    contrast: float = 1.4,
    brightness: float = 1.1,
    max_width: int = 680,
) -> Path:
    img = load_image(source)
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    gray = img.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    gray = ImageEnhance.Brightness(gray).enhance(brightness)
    gray = ImageEnhance.Sharpness(gray).enhance(1.5)
    if len(set(gray.resize((64, 64)).getdata())) < 40:
        gray = ImageOps.posterize(gray, bits=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gray.save(output_path, format="PNG", dpi=(300, 300))
    return output_path

