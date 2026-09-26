"""Majority-vote smoothing over 3x3 neighbourhoods."""

from pydantic import Field

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "smooth"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Smooth (majority vote)"
DESCRIPTION = (
    "A cell whose colour appears at most twice in its 3x3 neighbourhood takes the "
    "neighbourhood's majority colour. Each iteration is another full pass."
)


class Params(OpParams):
    iterations: int = Field(1, ge=1, le=5)


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.majority_vote_filter(to_indices(pattern), params.iterations))
