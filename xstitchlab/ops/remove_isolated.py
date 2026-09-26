"""Replace cells whose four cardinal neighbours are all another colour."""

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "remove_isolated"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Remove isolated cells"
DESCRIPTION = (
    "A cell with no cardinal neighbour of its own colour takes the most common "
    "neighbouring colour. Blocks of two or more cells are left alone."
)


class Params(OpParams):
    pass


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.remove_isolated_pixels(to_indices(pattern)))
