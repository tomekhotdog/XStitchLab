"""Complete 2x2 corners whose odd cell is isolated."""

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "rectangularize"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Rectangularize corners"
DESCRIPTION = (
    "Where three cells of a 2x2 block share a colour and the fourth has no cell of "
    "its colour outside the block, the fourth joins them. Conservative: in practice "
    "this fills enclosed single cells and leaves notches on region edges alone."
)


class Params(OpParams):
    pass


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.rectangularize(to_indices(pattern)))
