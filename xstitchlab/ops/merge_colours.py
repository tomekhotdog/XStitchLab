"""Fold one legend colour into another and drop it from the legend."""


from xstitchlab.ops._grid import keep_entries, to_indices
from xstitchlab.ops._legend import index_of_code
from xstitchlab.ops.base import OpError, OpParams

NAME = "merge_colours"
KIND = "pattern"
GROUP = "kit"
TITLE = "Merge colours"
DESCRIPTION = (
    "Every cell of `from_dmc` becomes `to_dmc` and `from_dmc` leaves the legend. "
    "If the background was `from_dmc` it becomes `to_dmc`."
)


class Params(OpParams):
    from_dmc: str
    to_dmc: str


def apply(pattern, params: Params):
    src = index_of_code(pattern, params.from_dmc)
    dst = index_of_code(pattern, params.to_dmc)
    if src == dst:
        raise OpError(f"from_dmc and to_dmc must differ (both are DMC {params.from_dmc})")
    return merge(pattern, src, dst)


def merge(pattern, src: int, dst: int):
    """`pattern` with legend entry `src` folded into `dst` and the legend compacted."""
    indices = to_indices(pattern)
    indices[indices == src] = dst
    keep = [i for i in range(len(pattern.legend)) if i != src]
    out = keep_entries(pattern, indices, keep)
    if pattern.background_index == src:
        out.background_index = keep.index(dst)
        out.count_stitches()
    return out
