"""Merge legend entries whose RGB are closer than a threshold."""

import numpy as np
from pydantic import Field

from xstitchlab.core import pixelator
from xstitchlab.ops._grid import from_indices, to_indices, to_palette
from xstitchlab.ops.base import OpParams

NAME = "merge_similar_colours"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Merge similar colours"
DESCRIPTION = (
    "Legend entries closer than `threshold` (Euclidean RGB distance) are merged, "
    "keeping the one with more cells. The background follows its entry wherever it goes."
)


class Params(OpParams):
    threshold: int = Field(20, ge=1, le=100)


def apply(pattern, params: Params):
    indices = to_indices(pattern)
    new_palette, new_indices = pixelator.merge_similar_colors(to_palette(pattern), indices, params.threshold)
    out = from_indices(pattern, new_indices, new_palette)
    out.background_index = _background_after(pattern, indices, new_indices, out.background_index)
    out.count_stitches()
    return out


def _background_after(pattern, indices: np.ndarray, new_indices: np.ndarray, by_rgb: int | None) -> int | None:
    """Where the background's cells went; falls back to the RGB match when it had none."""
    if pattern.background_index is None:
        return None
    moved = new_indices[indices == pattern.background_index]
    return int(moved[0]) if moved.size else by_rgb
