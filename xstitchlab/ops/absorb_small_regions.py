"""Absorb connected regions below a size into the dominant surrounding colour."""

from pydantic import Field

from xstitchlab.core import adjuster
from xstitchlab.ops._grid import from_indices, to_indices
from xstitchlab.ops.base import OpParams

NAME = "absorb_small_regions"
KIND = "pattern"
GROUP = "cleanup"
TITLE = "Absorb small regions"
DESCRIPTION = (
    "Connected regions with fewer than min_region_size cells take the most common "
    "colour along their border. Can erase thin lines: raise the size with care."
)


class Params(OpParams):
    min_region_size: int = Field(2, ge=2, le=64)


def apply(pattern, params: Params):
    return from_indices(pattern, adjuster.absorb_small_regions(to_indices(pattern), params.min_region_size))
