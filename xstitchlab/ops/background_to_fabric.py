"""Mark one legend entry as the fabric (background), leaving the grid untouched."""

import numpy as np

from xstitchlab.ops._grid import to_indices
from xstitchlab.ops._legend import index_of_code
from xstitchlab.ops.base import OpParams

NAME = "background_to_fabric"
KIND = "pattern"
GROUP = "kit"
TITLE = "Background to fabric"
DESCRIPTION = (
    "Leave one colour unstitched as bare fabric. `auto` picks the colour with the most "
    "cells on the outer border of the grid; otherwise give a DMC code from the legend. "
    "No cells change, only the stitch total."
)


class Params(OpParams):
    dmc_code: str = "auto"


def apply(pattern, params: Params):
    if params.dmc_code == "auto":
        index = _border_dominant(pattern)
    else:
        index = index_of_code(pattern, params.dmc_code)
    out = pattern.copy()
    out.background_index = index
    out.count_stitches()
    return out


def _border_dominant(pattern) -> int:
    """Legend index with the most cells on the outer ring; ties go to the lower index."""
    indices = to_indices(pattern)
    ring = np.ones(indices.shape, dtype=bool)
    ring[1:-1, 1:-1] = False
    counts = np.bincount(indices[ring], minlength=len(pattern.legend))
    return int(np.argmax(counts))
