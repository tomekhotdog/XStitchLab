"""Turn an image into a Pattern: resize to the stitch grid and map colours to DMC."""

from typing import Literal

import numpy as np
from PIL import Image
from pydantic import Field

from xstitchlab.core import pixelator
from xstitchlab.core.color_mapper import ColorMapper
from xstitchlab.core.pattern import SYMBOLS, ColorLegendEntry, Pattern, PatternMetadata
from xstitchlab.ops._image import target_size
from xstitchlab.ops.base import OpParams

NAME = "pixelate"
KIND = "pixelate"
GROUP = "import"
TITLE = "Pixelate to grid"
DESCRIPTION = (
    "Resize to the stitch grid (majority vote per block, or nearest pixel) and map "
    "every colour to its closest DMC thread. Height follows the aspect ratio when omitted."
)


class Params(OpParams):
    width: int = Field(50, ge=4, le=400)
    height: int | None = Field(None, ge=1, le=400)
    sample: Literal["majority", "nearest"] = "majority"
    steps: int = Field(3, ge=1, le=6)
    color_space: Literal["lab", "rgb"] = "lab"
    fabric_count: int = Field(14, ge=6, le=32)


def apply(img: Image.Image, params: Params) -> Pattern:
    img = img.convert("RGB")
    small = _resize(img, params)
    _, palette = pixelator.extract_unique_colors(small)
    indices = pixelator.get_color_indices(small, palette)
    dmc_colors = ColorMapper(use_lab=params.color_space == "lab").map_palette(palette)
    dmc_colors, indices = _merge_same_dmc(dmc_colors, indices)

    legend = [
        ColorLegendEntry(dmc, symbol=SYMBOLS[i] if i < len(SYMBOLS) else str(i))
        for i, dmc in enumerate(dmc_colors)
    ]
    pattern = Pattern(
        grid=indices.tolist(),
        legend=legend,
        metadata=PatternMetadata(title="", fabric_count=params.fabric_count),
    )
    pattern.background_index = pattern.guess_background_index()
    pattern.count_stitches()
    return pattern


def _resize(img: Image.Image, params: Params) -> Image.Image:
    width, height = target_size(img, params.width, params.height)
    if img.width <= width and img.height <= height:
        return img
    if params.sample == "nearest":
        return pixelator.resize_to_grid(img, width, height, maintain_aspect=False, resample_method="nearest")
    if params.steps > 1:
        return pixelator.multi_step_resize(img, width, height, num_steps=params.steps, mode="majority")
    return pixelator.boundary_preserving_resize(img, width, height, mode="majority")


def _merge_same_dmc(dmc_colors, indices: np.ndarray):
    """Palette colours that map to one DMC code share one legend entry (first wins)."""
    merged, first_index, remap = [], {}, []
    for dmc in dmc_colors:
        if dmc.code not in first_index:
            first_index[dmc.code] = len(merged)
            merged.append(dmc)
        remap.append(first_index[dmc.code])
    return merged, np.asarray(remap, dtype=np.int32)[indices]
