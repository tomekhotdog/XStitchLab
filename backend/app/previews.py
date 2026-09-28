"""Base64 PNG previews for the UI (thumbnails and per-step previews)."""

import base64
import io

from PIL import Image

from xstitchlab.core.pattern import Pattern
from xstitchlab.core.visualizer import render_color_preview


def image_png_b64(img: Image.Image, max_px: int = 400) -> str:
    """`img` as base64 PNG, shrunk so its longer side is at most `max_px`."""
    if max(img.size) > max_px:
        img = img.copy()
        img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def pattern_png_b64(pattern: Pattern, max_px: int = 400) -> str:
    """Colour preview of `pattern` as base64 PNG, longer side at most `max_px`."""
    cell = max(1, max_px // max(pattern.width, pattern.height, 1))
    img = render_color_preview(pattern, cell_size=cell, show_grid=cell >= 4)
    return image_png_b64(img, max_px)
