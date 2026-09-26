"""Backstitch along colour boundaries whose contrast exceeds a threshold.

`backstitch.detect_boundaries` already emits grid-corner coordinates: the edge
between cell (x, y) and the cell below it is (x, y+1)-(x+1, y+1), and the edge
between (x, y) and the cell to its right is (x+1, y)-(x+1, y+1), which is the
`Segment` convention (the edge on top of cell (x, y) is (x, y)-(x+1, y)). It
only ever emits horizontal and vertical edges, so `diagonals` currently changes
nothing; it is kept so recipes stay valid if diagonal detection is added.
"""

from pydantic import Field

from xstitchlab.core import backstitch
from xstitchlab.core.pattern import Segment
from xstitchlab.ops._grid import to_indices, to_palette
from xstitchlab.ops._segments import merge_collinear
from xstitchlab.ops.base import OpParams

NAME = "generate_backstitch"
KIND = "pattern"
GROUP = "outline"
TITLE = "Generate backstitch"
DESCRIPTION = (
    "Outline every boundary between colours at least min_contrast apart (Euclidean "
    "RGB, 0-441) with merged straight segments. replace=False adds to the existing "
    "backstitch instead; overlapping runs are merged so nothing is stitched twice."
)


class Params(OpParams):
    min_contrast: int = Field(50, ge=0, le=442)  # RGB distance; 442 > sqrt(3*255^2)
    diagonals: bool = False
    replace: bool = True


def apply(pattern, params: Params):
    found = backstitch.detect_boundaries(to_indices(pattern), to_palette(pattern), params.min_contrast)
    segments = [Segment(s.x1, s.y1, s.x2, s.y2) for s in found]
    if not params.diagonals:
        segments = [s for s in segments if s.x1 == s.x2 or s.y1 == s.y2]
    segments = merge_collinear(segments)
    if not params.replace:
        segments = merge_collinear(list(pattern.backstitch) + segments)
    out = pattern.copy()
    out.backstitch = segments
    return out
