"""Fill single cells enclosed by one colour on at least three sides."""

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "fill_holes"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Fill holes"
DESCRIPTION = (
    "A cell with three or four cardinal neighbours of one other colour takes that "
    "colour. Boundary cells (two-sided) are preserved."
)


class Params(OpParams):
    pass


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.fill_internal_holes(to_indices(pattern)))
