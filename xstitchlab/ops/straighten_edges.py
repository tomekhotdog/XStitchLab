"""Straighten region edges by resolving interior cells that differ from every cardinal neighbour."""

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "straighten_edges"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Straighten edges"
DESCRIPTION = (
    "An interior cell that matches none of its cardinal neighbours takes the colour "
    "at least two of them share. Aggressive: changes diagonal boundaries."
)


class Params(OpParams):
    pass


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.straighten_edges(to_indices(pattern)))
