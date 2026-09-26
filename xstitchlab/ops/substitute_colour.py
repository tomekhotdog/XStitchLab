"""Swap the thread of one legend entry for another DMC colour, cells untouched."""

from xstitchlab.ops import merge_colours
from xstitchlab.ops._legend import index_of_code, palette_colour
from xstitchlab.ops.base import OpParams

NAME = "substitute_colour"
KIND = "pattern"
GROUP = "kit"
TITLE = "Substitute colour"
DESCRIPTION = (
    "Replace the thread of `from_dmc` with DMC `to_dmc` (name and RGB from the palette); "
    "the cells and symbol stay. If `to_dmc` is already in the legend the two are merged."
)


class Params(OpParams):
    from_dmc: str
    to_dmc: str


def apply(pattern, params: Params):
    src = index_of_code(pattern, params.from_dmc)
    colour = palette_colour(params.to_dmc)
    already_there = any(
        i != src and entry.dmc_color.code == params.to_dmc for i, entry in enumerate(pattern.legend)
    )
    if already_there:
        return merge_colours.apply(pattern, merge_colours.Params(from_dmc=params.from_dmc, to_dmc=params.to_dmc))
    out = pattern.copy()
    out.legend[src].dmc_color = colour
    out.count_stitches()
    return out
