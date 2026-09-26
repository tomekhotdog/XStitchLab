"""Turn 2x2 checkerboards into stair steps."""

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "snap_diagonals"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Snap diagonals to stairs"
DESCRIPTION = (
    "Every 2x2 checkerboard of two colours becomes a horizontal or vertical stair "
    "step, whichever the surrounding cells support. Blocks are judged on the input, "
    "so a one-cell-wide diagonal line is shifted rather than stepped."
)


class Params(OpParams):
    pass


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.snap_diagonals_to_stairs(to_indices(pattern)))
