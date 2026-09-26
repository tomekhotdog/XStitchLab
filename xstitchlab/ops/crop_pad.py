"""Resize the canvas by translating the grid into a new frame; padding is fabric.

Every anchor reduces to one translation (dx, dy): source cell (x, y) lands on
(x + dx, y + dy), cells outside the target are cropped, and uncovered target
cells are the background. Backstitch moves with the cells and is clipped to the
frame (corner coordinates run 0..width and 0..height inclusive).
"""

from typing import Literal

import numpy as np
from pydantic import Field

from xstitchlab.core.pattern import ColorLegendEntry, Pattern, Segment
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops._legend import free_symbol, palette_colour
from xstitchlab.ops._segments import merge_collinear, split_to_units
from xstitchlab.ops.base import OpParams

NAME = "crop_pad"
KIND = "pattern"
GROUP = "kit"
TITLE = "Crop or pad canvas"
DESCRIPTION = (
    "Set the canvas to width x height. `fit_content` centres the box of stitched cells, "
    "`center` centres the whole grid, `offset` shifts by (offset_x, offset_y). New cells "
    "are background; without one, `pad_dmc` (auto = 3865 Winter White) becomes the background."
)

WINTER_WHITE = "3865"


class Params(OpParams):
    width: int = Field(50, ge=4, le=400)
    height: int = Field(50, ge=4, le=400)
    anchor: Literal["center", "fit_content", "offset"] = "fit_content"
    offset_x: int = 0
    offset_y: int = 0
    pad_dmc: str = "auto"


def apply(pattern, params: Params):
    indices = to_indices(pattern)
    dx, dy = _translation(indices, pattern.background_index, params)
    pattern = _with_background(pattern, params.pad_dmc)

    target = np.full((params.height, params.width), pattern.background_index, dtype=np.int32)
    src_h, src_w = indices.shape
    x0, x1 = max(0, -dx), min(src_w, params.width - dx)
    y0, y1 = max(0, -dy), min(src_h, params.height - dy)
    if x0 < x1 and y0 < y1:
        target[y0 + dy:y1 + dy, x0 + dx:x1 + dx] = indices[y0:y1, x0:x1]

    out = from_indices(pattern, target)
    out.backstitch = _translate_backstitch(pattern.backstitch, dx, dy, params.width, params.height)
    return out


def _translation(indices: np.ndarray, background: int | None, params: Params) -> tuple[int, int]:
    if params.anchor == "offset":
        return params.offset_x, params.offset_y
    h, w = indices.shape
    if params.anchor == "center":
        return (params.width - w) // 2, (params.height - h) // 2
    content = np.ones(indices.shape, dtype=bool) if background is None else indices != background
    if not content.any():
        return (params.width - w) // 2, (params.height - h) // 2
    ys, xs = np.nonzero(content)
    x_min, x_max, y_min, y_max = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    # Centre the box in the target; a box wider than the target is centre-cropped by the same formula.
    return (
        (params.width - (x_max - x_min + 1)) // 2 - x_min,
        (params.height - (y_max - y_min + 1)) // 2 - y_min,
    )


def _with_background(pattern: Pattern, pad_dmc: str) -> Pattern:
    """`pattern` unchanged if it has a background, else with `pad_dmc` (auto = Winter White) as background."""
    if pattern.background_index is not None:
        return pattern
    colour = palette_colour(WINTER_WHITE if pad_dmc == "auto" else pad_dmc)
    out = pattern.copy()
    existing = next((i for i, e in enumerate(out.legend) if e.dmc_color.code == colour.code), None)
    if existing is None:
        out.legend.append(ColorLegendEntry(colour, free_symbol(out)))
        existing = len(out.legend) - 1
    out.background_index = existing
    out.count_stitches()
    return out


def _translate_backstitch(segments: list[Segment], dx: int, dy: int, width: int, height: int) -> list[Segment]:
    def inside(x: int, y: int) -> bool:
        return 0 <= x <= width and 0 <= y <= height

    kept = []
    for s in segments:
        moved = Segment(s.x1 + dx, s.y1 + dy, s.x2 + dx, s.y2 + dy)
        if inside(moved.x1, moved.y1) and inside(moved.x2, moved.y2):
            kept.append(moved)
        else:
            kept.extend(u for u in split_to_units([moved]) if inside(u.x1, u.y1) and inside(u.x2, u.y2))
    return merge_collinear(kept)
