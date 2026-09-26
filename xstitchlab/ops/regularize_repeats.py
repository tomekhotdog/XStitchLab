"""Regularize repeated rectangles (windows, doors) and, optionally, near-duplicate columns."""

from pydantic import Field

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "regularize_repeats"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Regularize repeats"
DESCRIPTION = (
    "Groups of at least min_group_size same-colour rectangles of similar size are "
    "resized to their median size. With enforce_repetition, columns at least "
    "`similarity` alike are made identical by majority vote."
)


class Params(OpParams):
    min_group_size: int = Field(3, ge=2, le=20)
    enforce_repetition: bool = False
    similarity: float = Field(0.8, ge=0.5, le=1.0)


def apply(pattern, params: Params):
    indices = adjuster.regularize_rectangles(to_indices(pattern), min_group_size=params.min_group_size)
    if params.enforce_repetition:
        indices = adjuster.enforce_pattern_repetition(indices, similarity_threshold=params.similarity)
    return from_indices(pattern, indices)
