from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

from morning_paper.image_tools import load_image


def _write(path: Path, fmt: str) -> Path:
    Image.new("RGB", (4, 4), "white").save(path, format=fmt)
    return path


def test_load_image_accepts_web_formats(tmp_path: Path) -> None:
    for fmt, ext in (("PNG", "png"), ("JPEG", "jpg"), ("GIF", "gif"), ("WEBP", "webp")):
        with load_image(str(_write(tmp_path / f"a.{ext}", fmt))) as image:
            assert image.format == fmt


def test_load_image_rejects_non_web_formats(tmp_path: Path) -> None:
    for fmt, ext in (("TIFF", "tif"), ("BMP", "bmp")):
        with pytest.raises(UnidentifiedImageError):
            load_image(str(_write(tmp_path / f"a.{ext}", fmt)))
