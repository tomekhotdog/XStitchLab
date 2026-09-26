"""`_grid`: the Pattern <-> index-array boundary every pattern op goes through."""

import numpy as np
import pytest

from tests.ops.helpers import pattern_from_rows, rows_of
from xstitchlab.core.pattern import OpCall, Segment
from xstitchlab.ops import _grid
from xstitchlab.ops.base import OpError


def test_to_indices_and_to_palette_mirror_the_pattern():
    p = pattern_from_rows("012/210")
    indices = _grid.to_indices(p)
    assert indices.dtype == np.int32 and indices.shape == (2, 3)
    assert indices.tolist() == p.grid
    palette = _grid.to_palette(p)
    assert palette.dtype == np.uint8 and palette.shape == (3, 3)
    assert palette.tolist() == [list(e.dmc_color.rgb) for e in p.legend]


def test_from_indices_keeps_everything_but_the_grid_and_recounts():
    p = pattern_from_rows("000/010/000")
    p.backstitch = [Segment(1, 1, 2, 1)]
    p.recipe = [OpCall("noop")]
    p.metadata.title = "t"
    out = _grid.from_indices(p, np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]]))
    assert rows_of(out) == ["111", "101", "111"]
    assert rows_of(p) == ["000", "010", "000"]          # input untouched
    assert out.legend is not p.legend and [e.dmc_color for e in out.legend] == [e.dmc_color for e in p.legend]
    assert out.background_index == 0
    assert out.backstitch == [Segment(1, 1, 2, 1)] and out.recipe == [OpCall("noop")]
    assert out.metadata.title == "t"
    assert [e.stitch_count for e in out.legend] == [1, 8]
    assert out.metadata.total_stitches == 8


def test_from_indices_rejects_indices_outside_the_legend():
    p = pattern_from_rows("01/10")
    with pytest.raises(OpError, match="legend"):
        _grid.from_indices(p, np.array([[0, 2], [1, 0]]))


def test_from_indices_with_smaller_palette_remaps_legend_by_rgb():
    p = pattern_from_rows("012/012", background_index=2)
    palette = _grid.to_palette(p)[[2, 0]]                # keep terra cotta and white, drop black
    out = _grid.from_indices(p, np.array([[1, 1, 0], [1, 1, 0]]), palette)
    assert [e.dmc_color.code for e in out.legend] == ["3830", "3865"]
    assert out.background_index == 0                    # still the terra cotta entry
    assert rows_of(out) == ["110", "110"]
    assert [e.stitch_count for e in out.legend] == [2, 4]


def test_from_indices_with_palette_sets_background_none_when_its_rgb_is_gone():
    p = pattern_from_rows("012/012", background_index=1)
    palette = _grid.to_palette(p)[[0, 2]]
    out = _grid.from_indices(p, np.zeros((2, 3), dtype=int), palette)
    assert out.background_index is None


def test_from_indices_with_unknown_rgb_raises():
    p = pattern_from_rows("01/10")
    palette = np.array([[0, 0, 0], [1, 2, 3]], dtype=np.uint8)
    with pytest.raises(OpError, match="RGB"):
        _grid.from_indices(p, np.zeros((2, 2), dtype=int), palette)


def test_drop_unused_colours_reindexes_and_keeps_background_by_rgb():
    p = pattern_from_rows("002/002", n_colours=3, background_index=2)   # index 1 (black) unused
    out = _grid.drop_unused_colours(p)
    assert [e.dmc_color.code for e in out.legend] == ["3865", "3830"]
    assert rows_of(out) == ["001", "001"]
    assert out.background_index == 1
    assert out.legend[1].dmc_color.code == "3830"


def test_drop_unused_colours_keeps_a_zero_count_background():
    # Fabric may legitimately have no cells left (everything stitched), so the
    # background entry survives even at zero count.
    p = pattern_from_rows("11/11", n_colours=3, background_index=0)
    out = _grid.drop_unused_colours(p)
    assert [e.dmc_color.code for e in out.legend] == ["3865", "310"]
    assert out.background_index == 0
    assert rows_of(out) == ["11", "11"]


def test_drop_unused_colours_is_a_no_op_when_all_used():
    p = pattern_from_rows("01/12")
    out = _grid.drop_unused_colours(p)
    assert rows_of(out) == rows_of(p) and len(out.legend) == 3
