"""Pattern <-> index-array boundary for pattern ops (not an op: skipped by the registry).

Every pattern op reads the grid with `to_indices` (and the legend RGB with
`to_palette` when the core function needs it), transforms the array, and hands
the result to `from_indices`, which builds a fresh, recounted Pattern.
"""

import copy

import numpy as np

from xstitchlab.core.pattern import Pattern
from xstitchlab.ops.base import OpError


def to_indices(pattern: Pattern) -> np.ndarray:
    """Grid as an int32 (h, w) array."""
    return np.asarray(pattern.grid, dtype=np.int32)


def to_palette(pattern: Pattern) -> np.ndarray:
    """Legend RGB as a uint8 (n, 3) array, in legend order."""
    return np.array([entry.dmc_color.rgb for entry in pattern.legend], dtype=np.uint8).reshape(-1, 3)


def from_indices(pattern: Pattern, indices: np.ndarray, palette: np.ndarray | None = None) -> Pattern:
    """New Pattern with `indices` as the grid and everything else copied from `pattern`.

    Without `palette` the legend is kept as is (indices must fit it). With a
    `palette` of (n', 3) rows, row k becomes legend entry k: each row is matched
    to the first existing entry with identical RGB (OpError if none), so entries
    absent from `palette` are dropped. `background_index` keeps pointing at the
    same RGB, or becomes None when that RGB was dropped.
    """
    indices = np.asarray(indices)
    if indices.ndim != 2 or indices.size == 0:
        raise OpError(f"grid must be a non-empty 2-D array, got shape {indices.shape}")
    if palette is None:
        keep = list(range(len(pattern.legend)))
    else:
        keep = [_legend_index_of(pattern, rgb) for rgb in np.asarray(palette).reshape(-1, 3)]
    if indices.min() < 0 or indices.max() >= len(keep):
        raise OpError(f"grid index out of range for a legend of {len(keep)} entries")
    return rebuild(pattern, indices, keep)


def drop_unused_colours(pattern: Pattern) -> Pattern:
    """Remove legend entries with zero cells and reindex the grid compactly.

    The background entry is kept even at zero cells: fabric may legitimately
    have no unstitched cell left, and dropping it would lose the fabric choice.
    """
    indices = to_indices(pattern)
    counts = np.bincount(indices.ravel(), minlength=len(pattern.legend))
    keep = [i for i in range(len(pattern.legend)) if counts[i] > 0 or i == pattern.background_index]
    remap = np.full(len(pattern.legend), -1, dtype=np.int32)
    remap[keep] = np.arange(len(keep), dtype=np.int32)
    return rebuild(pattern, remap[indices], keep)


def _legend_index_of(pattern: Pattern, rgb) -> int:
    rgb = tuple(int(v) for v in rgb)
    for i, entry in enumerate(pattern.legend):
        if tuple(entry.dmc_color.rgb) == rgb:
            return i
    raise OpError(f"palette RGB {rgb} matches no legend entry")


def rebuild(pattern: Pattern, indices: np.ndarray, keep: list[int]) -> Pattern:
    """Pattern whose legend is `pattern.legend[k] for k in keep`, grid `indices`.

    `indices` must already be expressed in the new (compact) numbering. The
    background follows its entry's new position, or its RGB if the entry was
    dropped, or becomes None.
    """
    return Pattern(
        grid=indices.tolist(),
        legend=[copy.deepcopy(pattern.legend[k]) for k in keep],
        metadata=copy.deepcopy(pattern.metadata),
        backstitch=list(pattern.backstitch),
        background_index=_background_in(pattern, keep),
        recipe=copy.deepcopy(pattern.recipe),
    )


def _background_in(pattern: Pattern, keep: list[int]) -> int | None:
    old = pattern.background_index
    if old is None or old >= len(pattern.legend):
        return None
    if old in keep:
        return keep.index(old)
    rgb = tuple(pattern.legend[old].dmc_color.rgb)
    for new, k in enumerate(keep):
        if tuple(pattern.legend[k].dmc_color.rgb) == rgb:
            return new
    return None
