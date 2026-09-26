"""`_segments`: backstitch segment normalisation shared by generate_backstitch and outline_to_backstitch."""

import pytest

from xstitchlab.core.pattern import Segment
from xstitchlab.ops import _segments
from xstitchlab.ops._segments import merge_collinear
from xstitchlab.ops.base import OpError


def ring_units() -> list[Segment]:
    """The 12 unit edges around the 3x3 block occupying cells x,y in 1..3."""
    top = [Segment(x, 1, x + 1, 1) for x in range(1, 4)]
    bottom = [Segment(x, 4, x + 1, 4) for x in range(1, 4)]
    left = [Segment(1, y, 1, y + 1) for y in range(1, 4)]
    right = [Segment(4, y, 4, y + 1) for y in range(1, 4)]
    return top + bottom + left + right


def test_merge_collinear_turns_ring_of_units_into_four_sides():
    merged = _segments.merge_collinear(ring_units())
    assert merged == sorted(
        [Segment(1, 1, 4, 1), Segment(1, 4, 4, 4), Segment(1, 1, 1, 4), Segment(4, 1, 4, 4)],
        key=lambda s: (s.x1, s.y1, s.x2, s.y2),
    )


def test_merge_collinear_is_order_independent_and_ignores_direction():
    units = ring_units()
    reversed_units = [Segment(s.x2, s.y2, s.x1, s.y1) for s in reversed(units)]
    assert _segments.merge_collinear(reversed_units) == _segments.merge_collinear(units)


def test_merge_collinear_does_not_bridge_gaps():
    merged = _segments.merge_collinear([Segment(0, 0, 1, 0), Segment(2, 0, 3, 0)])
    assert merged == [Segment(0, 0, 1, 0), Segment(2, 0, 3, 0)]


def test_merge_collinear_leaves_diagonals_alone():
    diag = [Segment(0, 0, 1, 1), Segment(1, 1, 2, 2)]
    assert _segments.merge_collinear(diag) == diag


def test_split_to_units_inverts_merge_collinear():
    key = lambda s: (s.x1, s.y1, s.x2, s.y2)
    units = ring_units()
    split = _segments.split_to_units(_segments.merge_collinear(units))
    assert sorted(split, key=key) == sorted(units, key=key)


def test_split_to_units_splits_diagonals_and_rejects_other_slopes():
    assert _segments.split_to_units([Segment(2, 2, 0, 0)]) == [Segment(0, 0, 1, 1), Segment(1, 1, 2, 2)]
    with pytest.raises(OpError, match="45"):
        _segments.split_to_units([Segment(0, 0, 2, 1)])


def test_dedupe_removes_reversed_duplicates_and_keeps_first_order():
    segs = [Segment(3, 0, 0, 0), Segment(0, 0, 3, 0), Segment(0, 0, 0, 2), Segment(0, 2, 0, 0)]
    assert _segments.dedupe(segs) == [Segment(0, 0, 3, 0), Segment(0, 0, 0, 2)]


def test_merge_collinear_leaves_diagonals_whole():
    assert merge_collinear([Segment(0, 0, 3, 3)]) == [Segment(0, 0, 3, 3)]


def test_merge_collinear_collapses_overlapping_runs():
    merged = merge_collinear([Segment(0, 1, 1, 1), Segment(0, 1, 3, 1)])
    assert merged == [Segment(0, 1, 3, 1)]
