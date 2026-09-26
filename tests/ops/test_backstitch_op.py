"""generate_backstitch: contrast boundaries -> merged corner-coordinate segments."""

from tests.ops.helpers import pattern_from_rows, small_pattern
from xstitchlab.core.pattern import Segment
from xstitchlab.ops import generate_backstitch, registry

OUTER_RING = {Segment(1, 1, 4, 1), Segment(1, 4, 4, 4), Segment(1, 1, 1, 4), Segment(4, 1, 4, 4)}
CENTRE_RING = {Segment(2, 2, 3, 2), Segment(2, 3, 3, 3), Segment(2, 2, 2, 3), Segment(3, 2, 3, 3)}


def test_generates_merged_rings_around_contrasting_blocks():
    # Black/white (~425) and black/terra cotta (~215) both exceed 50, so the
    # ring around the 3x3 block and the ring around the centre cell are drawn.
    out = generate_backstitch.apply(small_pattern(), generate_backstitch.Params(min_contrast=50))
    assert set(out.backstitch) == OUTER_RING | CENTRE_RING
    assert len(out.backstitch) == 8
    assert out.backstitch == sorted(out.backstitch, key=lambda s: (s.x1, s.y1, s.x2, s.y2))
    assert out.grid == small_pattern().grid


def test_min_contrast_filters_low_contrast_boundaries():
    out = generate_backstitch.apply(small_pattern(), generate_backstitch.Params(min_contrast=230))
    assert set(out.backstitch) == OUTER_RING


def test_replace_true_drops_existing_segments():
    p = small_pattern()
    p.backstitch = [Segment(0, 0, 5, 0)]
    out = generate_backstitch.apply(p, generate_backstitch.Params(replace=True, min_contrast=230))
    assert set(out.backstitch) == OUTER_RING
    assert p.backstitch == [Segment(0, 0, 5, 0)]


def test_replace_false_appends_without_duplicates():
    p = small_pattern()
    p.backstitch = [Segment(0, 0, 5, 0), Segment(4, 1, 1, 1)]     # second is the top side, reversed
    out = generate_backstitch.apply(p, generate_backstitch.Params(replace=False, min_contrast=230))
    assert out.backstitch[0] == Segment(0, 0, 5, 0)
    assert set(out.backstitch) == {Segment(0, 0, 5, 0)} | OUTER_RING
    assert len(out.backstitch) == 5


def test_diagonals_false_yields_only_axis_aligned_segments():
    p = pattern_from_rows(["10", "01"])
    out = generate_backstitch.apply(p, generate_backstitch.Params(diagonals=False, min_contrast=0))
    assert out.backstitch
    assert all(s.x1 == s.x2 or s.y1 == s.y2 for s in out.backstitch)


def test_no_boundaries_gives_empty_backstitch():
    out = generate_backstitch.apply(pattern_from_rows(["00", "00"]), generate_backstitch.Params())
    assert out.backstitch == []


def test_registered_in_outline_group_and_stats_count_segments():
    entry = next(e for e in registry.schemas() if e["name"] == "generate_backstitch")
    assert entry["group"] == "outline" and entry["kind"] == "pattern"
    from xstitchlab.core.pattern import OpCall
    result = registry.run_pattern_ops(small_pattern(), [OpCall("generate_backstitch", {"min_contrast": 230})])
    assert result.steps[0].stats["backstitch"] == 4
