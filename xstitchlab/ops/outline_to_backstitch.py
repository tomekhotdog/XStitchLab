"""Turn a drawn outline colour into backstitch and dissolve its cells.

1. O = cells of the outline colour.
2. Every unit edge with exactly one side in O (the grid boundary counts as
   outside O) becomes backstitch, merged into straight runs and added to the
   existing backstitch.
3. Unless `keep_cells`: each O cell takes the majority colour of its
   4-neighbours that are not in O (ties -> lower legend index), pass by pass
   so cells deep inside the outline wait for their neighbours to settle. When
   a pass makes no progress (an O region with no non-O neighbour at all) the
   remaining cells take the background, or without one the most common
   non-outline colour, or failing that the first non-outline legend entry;
   a legend holding only the outline colour is an OpError. Unused entries are
   then dropped, so the outline colour leaves the legend.
"""

import numpy as np

from xstitchlab.core.pattern import Segment
from xstitchlab.ops._grid import drop_unused_colours, from_indices, to_indices
from xstitchlab.ops._legend import index_of_code
from xstitchlab.ops._segments import merge_collinear
from xstitchlab.ops.base import OpError, OpParams

NAME = "outline_to_backstitch"
KIND = "pattern"
GROUP = "outline"
TITLE = "Outline to backstitch"
DESCRIPTION = (
    "Trace the edges of one colour's cells as backstitch (auto = the darkest non-background "
    "colour) and, unless keep_cells, fill those cells with their neighbouring colours so the "
    "outline colour leaves the legend."
)

_NEIGHBOURS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class Params(OpParams):
    outline_dmc: str = "auto"
    keep_cells: bool = False


def apply(pattern, params: Params):
    outline = _outline_index(pattern, params.outline_dmc)
    indices = to_indices(pattern)
    mask = indices == outline
    segments = merge_collinear(list(pattern.backstitch) + _edges_around(mask))
    if params.keep_cells:
        out = pattern.copy()
        out.backstitch = segments
        return out
    filled = _dissolve(pattern, indices, mask, outline)
    out = from_indices(pattern, filled)
    out.backstitch = segments
    return drop_unused_colours(out)


def _outline_index(pattern, outline_dmc: str) -> int:
    background = pattern.background_index
    if outline_dmc != "auto":
        index = index_of_code(pattern, outline_dmc)
        if index == background:
            raise OpError(f"DMC {outline_dmc} is the background; it cannot be the outline colour")
        return index
    candidates = [
        (0.299 * r + 0.587 * g + 0.114 * b, i)
        for i, (r, g, b) in ((i, e.dmc_color.rgb) for i, e in enumerate(pattern.legend))
        if i != background
    ]
    if not candidates:
        raise OpError("no non-background colour to use as the outline")
    return min(candidates)[1]


def _edges_around(mask: np.ndarray) -> list[Segment]:
    """Unit edges with exactly one side in `mask` (outside the grid counts as not in it)."""
    padded = np.pad(mask, 1, constant_values=False)
    h, w = mask.shape
    edges = []
    horizontal = padded[:-1, 1:-1] != padded[1:, 1:-1]          # (h+1, w): edge on top of row y
    for y, x in zip(*np.nonzero(horizontal)):
        edges.append(Segment(int(x), int(y), int(x) + 1, int(y)))
    vertical = padded[1:-1, :-1] != padded[1:-1, 1:]            # (h, w+1): edge left of column x
    for y, x in zip(*np.nonzero(vertical)):
        edges.append(Segment(int(x), int(y), int(x), int(y) + 1))
    return edges


def _dissolve(pattern, indices: np.ndarray, mask: np.ndarray, outline: int) -> np.ndarray:
    """Grid with every `mask` cell recoloured by the majority of its settled 4-neighbours."""
    indices = indices.copy()
    remaining = mask.copy()
    ys, xs = np.ogrid[: indices.shape[0], : indices.shape[1]]
    while remaining.any():
        votes = np.zeros((len(pattern.legend),) + indices.shape, dtype=np.int32)
        for dy, dx in _NEIGHBOURS:
            neighbour = _shift(indices, dy, dx, fill=0)
            settled = _shift(~remaining, dy, dx, fill=False)
            votes[neighbour, ys, xs] += settled                  # one vote per settled neighbour
        decided = remaining & (votes.sum(axis=0) > 0)
        if not decided.any():
            indices[remaining] = _fallback(pattern, indices, remaining, outline)
            break
        indices[decided] = votes.argmax(axis=0)[decided]          # argmax: ties -> lower index
        remaining &= ~decided
    return indices


def _shift(a: np.ndarray, dy: int, dx: int, fill) -> np.ndarray:
    """`a` moved so that out[y, x] = a[y + dy, x + dx], `fill` where that is off-grid."""
    out = np.full_like(a, fill)
    h, w = a.shape
    ys, yd = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
    xs, xd = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
    out[yd, xd] = a[ys, xs]
    return out


def _fallback(pattern, indices: np.ndarray, remaining: np.ndarray, outline: int) -> int:
    if pattern.background_index is not None:
        return pattern.background_index
    counts = np.bincount(indices[~remaining], minlength=len(pattern.legend))
    counts[outline] = 0
    if counts.any():
        return int(np.argmax(counts))
    others = [i for i in range(len(pattern.legend)) if i != outline]
    if not others:
        raise OpError("the legend holds only the outline colour; nothing to fill its cells with")
    return others[0]
