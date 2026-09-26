"""Helpers shared by the image-stage ops (not an op: skipped by the registry)."""

from PIL import Image


def target_size(img: Image.Image, width: int, height: int | None) -> tuple[int, int]:
    """Requested grid size; a missing height preserves the aspect ratio (rounded, at least 1)."""
    if height is None:
        height = max(1, round(width * img.height / img.width))
    return width, height
