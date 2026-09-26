"""Bridge one-cell gaps in boundary lines."""

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "connect_lines"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Connect broken lines"
DESCRIPTION = (
    "A cell flanked on both sides by one colour, with no support of its own colour "
    "across the line, takes the flanking colour (A B A -> A A A)."
)


class Params(OpParams):
    pass


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.connect_broken_lines(to_indices(pattern)))
