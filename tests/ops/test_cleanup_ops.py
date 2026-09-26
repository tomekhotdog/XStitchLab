"""Cleanup ops: each wraps one adjuster function behind the Pattern -> Pattern contract."""

import numpy as np
import pytest

from tests.ops.helpers import pattern_from_rows, rows_of
from xstitchlab.core.pattern import ColorLegendEntry, DMCColor, OpCall, Pattern
from xstitchlab.ops import (
    absorb_small_regions,
    connect_lines,
    defaults,
    fill_holes,
    merge_similar_colours,
    rectangularize,
    registry,
    regularize_repeats,
    remove_isolated,
    smooth,
    snap_diagonals,
    straighten_edges,
)

CLEANUP_OPS = [
    remove_isolated, absorb_small_regions, smooth, straighten_edges, fill_holes,
    snap_diagonals, connect_lines, rectangularize, regularize_repeats,
]

NOISY = [
    "0000000000",
    "0111101110",
    "0101101010",
    "0111101110",
    "0000200000",
    "0022222200",
    "0020000200",
    "0022222200",
    "0000010000",
    "0000000000",
]


def assert_well_formed(out: Pattern, like: Pattern) -> None:
    assert isinstance(out, Pattern)
    assert (out.width, out.height) == (like.width, like.height)
    values = set(np.unique(np.array(out.grid)).tolist())
    assert values <= set(range(len(out.legend)))
    assert sum(e.stitch_count for e in out.legend) == out.width * out.height


# --- invariants shared by every cleanup op ---------------------------------

@pytest.mark.parametrize("op", CLEANUP_OPS, ids=lambda op: op.NAME)
def test_cleanup_op_returns_well_formed_pattern_and_leaves_input_alone(op):
    p = pattern_from_rows(NOISY)
    before = rows_of(p)
    out = op.apply(p, op.Params())
    assert_well_formed(out, p)
    assert rows_of(p) == before
    assert out.background_index == 0
    assert out.legend is not p.legend


# --- remove_isolated ---------------------------------------------------------

def test_remove_isolated_absorbs_a_single_stray_cell():
    p = pattern_from_rows(["0000000"] * 3 + ["0001000"] + ["0000000"] * 3)
    out = remove_isolated.apply(p, remove_isolated.Params())
    assert rows_of(out) == ["0000000"] * 7


def test_remove_isolated_keeps_a_two_by_two_block():
    rows = ["0000000", "0000000", "0011000", "0011000", "0000000", "0000000", "0000000"]
    out = remove_isolated.apply(pattern_from_rows(rows), remove_isolated.Params())
    assert rows_of(out) == rows


# --- fill_holes --------------------------------------------------------------

def test_fill_holes_fills_a_one_cell_hole_and_leaves_the_border():
    rows = ["0000000", "0111110", "0111110", "0110110", "0111110", "0111110", "0000000"]
    out = fill_holes.apply(pattern_from_rows(rows), fill_holes.Params())
    assert rows_of(out) == ["0000000", "0111110", "0111110", "0111110", "0111110", "0111110", "0000000"]


# --- absorb_small_regions ----------------------------------------------------

def test_absorb_small_regions_drops_two_cells_but_keeps_three():
    rows = ["0000000", "0110000", "0000000", "0000000", "0011100", "0000000", "0000000"]
    out = absorb_small_regions.apply(pattern_from_rows(rows), absorb_small_regions.Params(min_region_size=3))
    assert rows_of(out) == ["0000000", "0000000", "0000000", "0000000", "0011100", "0000000", "0000000"]


# --- rectangularize ----------------------------------------------------------

def test_rectangularize_leaves_an_l_shape_alone_but_fills_an_enclosed_hole():
    # Current adjuster behaviour: it completes a 2x2 block only when the outlier
    # cell has no same-colour cardinal neighbour outside the block. In an L the
    # outlier is the surrounding colour, which always continues outside the
    # block, so nothing is "squared off". The only thing it fills is a cell
    # entirely enclosed by another colour.
    l_rows = ["0000000", "0100000", "0100000", "0111100", "0000000"]
    assert rows_of(rectangularize.apply(pattern_from_rows(l_rows), rectangularize.Params())) == l_rows
    hole = ["00000", "01110", "01010", "01110", "00000"]
    out = rectangularize.apply(pattern_from_rows(hole), rectangularize.Params())
    assert rows_of(out) == ["00000", "01110", "01110", "01110", "00000"]


# --- snap_diagonals ----------------------------------------------------------

def checkerboards(pattern: Pattern) -> list[tuple[int, int]]:
    a = np.array(pattern.grid)
    h, w = a.shape
    return [
        (y, x) for y in range(h - 1) for x in range(w - 1)
        if a[y, x] == a[y + 1, x + 1] and a[y, x + 1] == a[y + 1, x] and a[y, x] != a[y, x + 1]
    ]


def test_snap_diagonals_turns_a_lone_diagonal_pair_into_a_stair():
    # One 2x2 checkerboard; no neighbours favour vertical stairs, so the
    # pair is laid flat. The promise: that checkerboard is gone afterwards.
    p = pattern_from_rows(["0000", "0100", "0010", "0000"])
    assert checkerboards(p) == [(1, 1)]
    out = snap_diagonals.apply(p, snap_diagonals.Params())
    assert rows_of(out) == ["0000", "0110", "0000", "0000"]
    assert checkerboards(out) == []


def test_snap_diagonals_on_a_one_wide_line_shifts_it_and_leaves_checkerboards():
    # Documented current behaviour, not a promise: every 2x2 block along a
    # 1-wide diagonal is a checkerboard and each is resolved independently
    # (from the original), so the line is moved one cell right and shortened
    # rather than turned into stairs. The op is meant for region boundaries.
    p = pattern_from_rows(["100000", "010000", "001000", "000100", "000010", "000001"])
    out = snap_diagonals.apply(p, snap_diagonals.Params())
    assert rows_of(out) == ["110000", "001000", "000100", "000010", "000001", "000000"]
    assert len(checkerboards(out)) == 4


# --- merge_similar_colours ---------------------------------------------------

def test_merge_similar_colours_folds_close_entries_and_keeps_background():
    p = pattern_from_rows(["0011", "0011", "0022", "0022"], background_index=1)
    # Make index 2 sit 10 RGB units from index 1 (black).
    p.legend[2] = ColorLegendEntry(DMCColor("3799x", "Near Black", (0, 0, 10)), p.legend[2].symbol)
    out = merge_similar_colours.apply(p, merge_similar_colours.Params(threshold=30))
    assert len(out.legend) == 2
    assert set(np.unique(np.array(out.grid)).tolist()) <= {0, 1}
    assert rows_of(out) == ["0011", "0011", "0011", "0011"]
    assert out.background_index == 1
    assert out.legend[1].stitch_count == 8                      # 4 + 4
    assert out.legend[1].dmc_color.code == "310"                # both had 4 cells: first wins


def test_merge_similar_colours_background_follows_the_surviving_entry():
    # Background (black) is the smaller of the pair, so it is folded into the
    # near-black entry, and background_index must follow it there.
    p = pattern_from_rows(["0122", "0122", "0122", "0122"], background_index=1)
    p.legend[2] = ColorLegendEntry(DMCColor("3799x", "Near Black", (0, 0, 10)), p.legend[2].symbol)
    out = merge_similar_colours.apply(p, merge_similar_colours.Params(threshold=30))
    assert [e.dmc_color.code for e in out.legend] == ["3865", "3799x"]
    assert out.background_index == 1
    assert out.legend[1].stitch_count == 12
    assert out.metadata.total_stitches == 4


def test_merge_similar_colours_leaves_distinct_colours_alone():
    p = pattern_from_rows(["012", "012"])
    out = merge_similar_colours.apply(p, merge_similar_colours.Params(threshold=30))
    assert len(out.legend) == 3 and rows_of(out) == ["012", "012"]


# --- registry / defaults -----------------------------------------------------

def test_registry_lists_all_new_ops_with_groups():
    entries = {e["name"]: e for e in registry.schemas()}
    for op in CLEANUP_OPS:
        assert (entries[op.NAME]["kind"], entries[op.NAME]["group"]) == ("pattern", "cleanup")
    assert (entries["merge_similar_colours"]["kind"], entries["merge_similar_colours"]["group"]) == ("pattern", "cleanup")
    assert (entries["generate_backstitch"]["kind"], entries["generate_backstitch"]["group"]) == ("pattern", "outline")


def test_predesigned_default_runs_the_cleanup_tail():
    assert [c.op for c in defaults.PREDESIGNED] == [
        "quantize_image", "pixelate", "remove_isolated", "fill_holes",
        "snap_diagonals", "connect_lines", "rectangularize",
    ]
    assert [c.params for c in defaults.PREDESIGNED[2:]] == [{}] * 5
    registry.validate_recipe(defaults.PREDESIGNED)
    assert [c.op for c in defaults.PHOTO] == ["resize_image", "quantize_image", "pixelate"]


def test_cleanup_ops_run_through_the_registry():
    p = pattern_from_rows(NOISY)
    result = registry.run_pattern_ops(p, [OpCall("remove_isolated"), OpCall("smooth", {"iterations": 2})])
    assert [s.name for s in result.steps] == ["remove_isolated", "smooth"]
    assert_well_formed(result.pattern, p)
