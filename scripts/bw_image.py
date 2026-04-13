#!/usr/bin/env python3
"""
Visual of the Day — B&W Printer Optimization
=============================================
Loads an image from a URL or local path, converts to high-contrast B&W for laser printing,
adjusts brightness/contrast for legibility, saves to a path for embedding.

Usage:
  python3 bw_image.py <image_source> [--output /path/to/output.png]
                           [--contrast 1.4] [--brightness 1.1]
                           [--threshold 128] [--caption "Visual of the day"]

Devon's Morning Brief use case:
  - Tweet/article images become B&W print-ready
  - Charts, diagrams, screenshots
  - Output embedded directly in markdown as: ![Caption](file://path)
"""

import sys
import argparse
import urllib.request
import urllib.error
from pathlib import Path

TRY_PIL = True
try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    TRY_PIL = False


def download_image(url: str) -> Image.Image:
    """Fetch image from URL, return PIL Image."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    from io import BytesIO
    return Image.open(BytesIO(data))


def open_local_image(path: str) -> Image.Image:
    """Open an image from a local path or file:// URI."""
    normalized = path[7:] if path.startswith("file://") else path
    return Image.open(Path(normalized).expanduser())


def load_image(source: str) -> Image.Image:
    """Load image from URL or local filesystem."""
    if source.startswith("http://") or source.startswith("https://"):
        return download_image(source)
    return open_local_image(source)


def process_for_print(
    img: Image.Image,
    contrast: float = 1.4,
    brightness: float = 1.1,
    threshold: int = 128,
    max_width: int = 680  # max pixels wide for print (≈ 7" at 100dpi)
) -> Image.Image:
    """
    Convert any image to print-ready B&W for Courier Prime 9pt layout.
    
    Steps:
    1. Resize if wider than max_width (maintain aspect ratio)
    2. Convert to grayscale
    3. Apply contrast enhancement
    4. Apply brightness correction
    5. Apply sharpening to recover line quality lost in B&W
    6. Apply posterize to pure B&W if the image has clean edges (charts/diagrams)
       — threshold determines the cutoff
    """
    # 1. Resize
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # 2. Grayscale
    gray = img.convert('L')  # 8-bit grayscale

    # 3. Contrast
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(contrast)

    # 4. Brightness
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(gray)
        gray = enhancer.enhance(brightness)

    # 5. Sharpen — critical for charts, graphs, screenshots
    enhancer = ImageEnhance.Sharpness(gray)
    gray = enhancer.enhance(1.5)

    # 6. Optional posterize to pure B&W for clean diagrams
    # Detect if image is "clean" (fewer than 30 distinct gray values → diagram/screenshot)
    import numpy as np
    arr = np.array(gray)
    distinct = len(np.unique(arr))
    if distinct < 40:
        # Looks like a chart/diagram — posterize to clean 2-bit B&W
        gray = ImageOps.posterize(gray, bits=2)

    return gray


def embed_markdown(img_path: str, caption: str = "", alt: str = "") -> str:
    """Return markdown image tag with optional caption."""
    alt_text = alt or caption or "Visual of the day"
    markdown = f'![{alt_text}](file://{img_path})'
    if caption:
        return markdown + f"\n\n*{caption}*"
    return markdown


def main():
    parser = argparse.ArgumentParser(description="Visual of the Day — B&W print optimizer")
    parser.add_argument("source", help="Image URL or local path to process")
    parser.add_argument("--output", "-o", default=None, help="Output PNG path")
    parser.add_argument("--contrast", "-c", type=float, default=1.4,
                        help="Contrast multiplier (default: 1.4)")
    parser.add_argument("--brightness", "-b", type=float, default=1.1,
                        help="Brightness multiplier (default: 1.1)")
    parser.add_argument("--threshold", "-t", type=int, default=128,
                        help="B&W threshold 0-255 (default: 128)")
    parser.add_argument("--max-width", "-w", type=int, default=680,
                        help="Max width in pixels (default: 680)")
    parser.add_argument("--caption", default="Visual of the day",
                        help="Caption used in the markdown snippet")
    parser.add_argument("--alt", default="",
                        help="Alt text override for the markdown snippet")
    args = parser.parse_args()

    if not TRY_PIL:
        print("ERROR: PIL (Pillow) not installed. Run: pip3 install Pillow", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"Loading: {args.source}", file=sys.stderr)
        img = load_image(args.source)
        print(f"  Original: {img.size[0]}x{img.size[1]} {img.mode}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR loading image: {e}", file=sys.stderr)
        sys.exit(1)

    processed = process_for_print(
        img,
        contrast=args.contrast,
        brightness=args.brightness,
        threshold=args.threshold,
        max_width=args.max_width
    )

    output_path = args.output or f"/tmp/visual-of-day.png"
    processed.save(output_path, format='PNG', dpi=(300, 300))
    print(f"Saved: {output_path}", file=sys.stderr)
    print(f"  Output: {processed.size[0]}x{processed.size[1]} B&W", file=sys.stderr)

    # Print the markdown embed tag
    print()
    print(embed_markdown(output_path, args.caption, args.alt))


if __name__ == "__main__":
    main()
