"""Base64 PNG previews for the UI (thumbnails and per-step previews)."""

import base64
import io

import numpy as np
from PIL import Image

from xstitchlab.core.pattern import Pattern

FABRIC_RGB = (246, 241, 231)


def image_png_b64(img: Image.Image, max_px: int = 400) -> str:
    """`img` as base64 PNG, shrunk so its longer side is at most `max_px`."""
    if max(img.size) > max_px:
        img = img.copy()
        img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def pattern_png_b64(pattern: Pattern, max_px: int = 400) -> str:
    """Colour preview of `pattern` as base64 PNG, longer side at most `max_px`.

    Built as one numpy lookup and a nearest-neighbour upscale, so a 400x400
    pattern costs milliseconds (the visualizer draws a rectangle per cell).
    """
    palette = np.array([e.dmc_color.rgb for e in pattern.legend] or [FABRIC_RGB], dtype=np.uint8)
    if pattern.background_index is not None and pattern.background_index < len(palette):
        palette[pattern.background_index] = FABRIC_RGB
    grid = np.asarray(pattern.grid, dtype=np.int64)
    grid = np.clip(grid, 0, len(palette) - 1)
    img = Image.fromarray(palette[grid], "RGB")
    cell = max(1, max_px // max(pattern.width, pattern.height, 1))
    if cell > 1:
        img = img.resize((pattern.width * cell, pattern.height * cell), Image.Resampling.NEAREST)
    return image_png_b64(img, max_px)
