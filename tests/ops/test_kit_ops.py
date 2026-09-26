"""Kit ops: the mechanical legend/canvas/outline edits that turn pipeline output into a kit."""

from collections import Counter

import pytest

from tests.ops.helpers import pattern_from_rows, rows_of, small_pattern
from xstitchlab.core.pattern import ColorLegendEntry, DMCColor, Pattern, Segment
from xstitchlab.ops import (
    background_to_fabric,
    crop_pad,
    merge_colours,
    outline_to_backstitch,
    registry,
    substitute_colour,
)
from xstitchlab.ops.base import OpError


def counts_by_code(pattern) -> dict[str, int]:
    return {e.dmc_color.code: e.stitch_count for e in pattern.legend}


# --- background_to_fabric ----------------------------------------------------

def test_background_auto_picks_the_border_dominant_colour_not_the_most_common():
    # Index 1 fills the whole inside (25 cells); index 0 owns the border ring (24 cells).
    rows = ["0000000", "0111110", "0111110", "0111110", "0111110", "0111110", "0000000"]
    p = pattern_from_rows(rows, background_index=None)
    assert p.legend[1].stitch_count > p.legend[0].stitch_count
    out = background_to_fabric.apply(p, background_to_fabric.Params())
    assert out.background_index == 0
    assert rows_of(out) == rows
    assert p.background_index is None


def test_background_by_code_changes_no_cells_and_only_the_total_drops():
    p = small_pattern()                                   # background 0 (white)
    before = counts_by_code(p)
    out = background_to_fabric.apply(p, background_to_fabric.Params(dmc_code="310"))
    assert out.background_index == 1
    assert counts_by_code(out) == before
    assert out.grid == p.grid
    assert out.metadata.total_stitches == 25 - before["310"]
    assert p.background_index == 0


def test_background_auto_ties_go_to_the_lower_index():
    p = pattern_from_rows(["0011", "0011"], background_index=None)   # border: 4 of each
    assert background_to_fabric.apply(p, background_to_fabric.Params()).background_index == 0


def test_background_unknown_code_is_an_op_error():
    with pytest.raises(OpError, match="4444"):
        background_to_fabric.apply(small_pattern(), background_to_fabric.Params(dmc_code="4444"))


# --- merge_colours -----------------------------------------------------------

def test_merge_colours_folds_from_into_to_and_reindexes_compactly():
    p = small_pattern()
    out = merge_colours.apply(p, merge_colours.Params(from_dmc="310", to_dmc="3830"))
    assert [e.dmc_color.code for e in out.legend] == ["3865", "3830"]
    assert max(v for row in out.grid for v in row) < len(out.legend)
    assert rows_of(out) == ["00000", "01110", "01110", "01110", "00000"]
    assert counts_by_code(out) == {"3865": 16, "3830": 9}      # 8 + 1
    assert out.background_index == 0
    assert rows_of(p) == rows_of(small_pattern())


def test_merge_colours_background_becomes_to_when_it_was_from():
    p = pattern_from_rows(["0012", "0012"], background_index=0)
    out = merge_colours.apply(p, merge_colours.Params(from_dmc="3865", to_dmc="3830"))
    assert [e.dmc_color.code for e in out.legend] == ["310", "3830"]
    assert out.background_index == 1
    assert rows_of(out) == ["1101", "1101"]
    assert out.metadata.total_stitches == 2


def test_merge_colours_background_follows_a_third_entry_when_it_shifts():
    p = pattern_from_rows(["0012", "0012"], background_index=2)
    out = merge_colours.apply(p, merge_colours.Params(from_dmc="3865", to_dmc="310"))
    assert [e.dmc_color.code for e in out.legend] == ["310", "3830"]
    assert out.background_index == 1
    assert rows_of(out) == ["0001", "0001"]


@pytest.mark.parametrize("from_dmc,to_dmc,msg", [
    ("4444", "310", "4444"),
    ("310", "4444", "4444"),
    ("310", "310", "differ"),
])
def test_merge_colours_rejects_unknown_or_identical_codes(from_dmc, to_dmc, msg):
    with pytest.raises(OpError, match=msg):
        merge_colours.apply(small_pattern(), merge_colours.Params(from_dmc=from_dmc, to_dmc=to_dmc))


# --- substitute_colour -------------------------------------------------------

def test_substitute_replaces_the_legend_entry_in_place_from_the_palette():
    p = small_pattern()
    out = substitute_colour.apply(p, substitute_colour.Params(from_dmc="3830", to_dmc="3777"))
    assert out.grid == p.grid
    entry = out.legend[2]
    assert (entry.dmc_color.code, entry.dmc_color.name, entry.dmc_color.rgb) == ("3777", "Terra Cotta Very Dark", (134, 48, 34))
    assert entry.symbol == p.legend[2].symbol
    assert out.background_index == 0
    assert len(out.legend) == 3
    assert p.legend[2].dmc_color.code == "3830"


def test_substitute_into_an_existing_legend_colour_merges():
    p = small_pattern()
    via_substitute = substitute_colour.apply(p, substitute_colour.Params(from_dmc="310", to_dmc="3830"))
    via_merge = merge_colours.apply(p, merge_colours.Params(from_dmc="310", to_dmc="3830"))
    assert via_substitute.grid == via_merge.grid
    assert [e.dmc_color for e in via_substitute.legend] == [e.dmc_color for e in via_merge.legend]
    assert via_substitute.background_index == via_merge.background_index == 0


@pytest.mark.parametrize("from_dmc,to_dmc", [("4444", "310"), ("310", "not-a-dmc")])
def test_substitute_rejects_unknown_codes(from_dmc, to_dmc):
    with pytest.raises(OpError):
        substitute_colour.apply(small_pattern(), substitute_colour.Params(from_dmc=from_dmc, to_dmc=to_dmc))


# --- crop_pad ----------------------------------------------------------------

def test_fit_content_centres_the_content_box_and_keeps_every_stitched_cell():
    p = small_pattern()                                  # 3x3 block at rows/cols 1..3 of 5x5
    out = crop_pad.apply(p, crop_pad.Params(width=7, height=7, anchor="fit_content"))
    assert (out.width, out.height) == (7, 7)
    assert rows_of(out) == [
        "0000000",
        "0000000",
        "0011100",
        "0012100",
        "0011100",
        "0000000",
        "0000000",
    ]
    before, after = counts_by_code(p), counts_by_code(out)
    assert {k: v for k, v in after.items() if k != "3865"} == {k: v for k, v in before.items() if k != "3865"}
    assert out.background_index == 0
    assert (out.metadata.width, out.metadata.height) == (7, 7)


def test_fit_content_centre_crops_a_box_larger_than_the_target():
    # Content spans all 6 columns (box centre 3.0); target width 4 -> keep columns 1..4.
    p = pattern_from_rows(["123456", "123456"], n_colours=7, background_index=0)
    out = crop_pad.apply(p, crop_pad.Params(width=4, height=4, anchor="fit_content"))
    assert rows_of(out) == ["0000", "2345", "2345", "0000"]


def test_center_anchors_the_whole_grid():
    p = pattern_from_rows(["11111", "11111", "11111", "11111", "11111"], n_colours=2)
    out = crop_pad.apply(p, crop_pad.Params(width=7, height=7, anchor="center"))
    assert rows_of(out) == ["0000000"] + ["0111110"] * 5 + ["0000000"]


def test_offset_translates_cells_and_backstitch():
    p = small_pattern()
    p.backstitch = [Segment(1, 1, 4, 1), Segment(1, 1, 1, 4)]
    out = crop_pad.apply(p, crop_pad.Params(width=10, height=10, anchor="offset", offset_x=2, offset_y=1))
    assert rows_of(out)[2][3:6] == "111" and rows_of(out)[3][3:6] == "121"
    assert set(out.backstitch) == {Segment(3, 2, 6, 2), Segment(3, 2, 3, 5)}


def test_negative_offset_crops_and_clips_backstitch():
    p = pattern_from_rows(["0000000000"] * 10)
    p.backstitch = [
        Segment(7, 1, 9, 1),      # entirely outside after crop: dropped
        Segment(2, 2, 8, 2),      # straddles: only the inside run survives
        Segment(0, 0, 5, 5),      # diagonal, fully inside (far edge is inclusive)
        Segment(0, 3, 8, 3),
    ]
    out = crop_pad.apply(p, crop_pad.Params(width=5, height=5, anchor="offset"))
    assert (out.width, out.height) == (5, 5)
    assert set(out.backstitch) == {Segment(2, 2, 5, 2), Segment(0, 0, 5, 5), Segment(0, 3, 5, 3)}


def test_offset_moves_content_out_of_frame_gracefully():
    p = small_pattern()
    out = crop_pad.apply(p, crop_pad.Params(width=5, height=5, anchor="offset", offset_x=-2, offset_y=-2))
    assert rows_of(out) == ["21000", "11000", "00000", "00000", "00000"]


def test_pad_with_no_background_adds_winter_white_as_background():
    black = ColorLegendEntry(DMCColor("310", "Black", (0, 0, 0)), "●")
    p = Pattern(grid=[[0, 0], [0, 0]], legend=[black], background_index=None)
    out = crop_pad.apply(p, crop_pad.Params(width=4, height=4, anchor="center"))
    assert [e.dmc_color.code for e in out.legend] == ["310", "3865"]
    assert out.legend[1].dmc_color.name == "Winter White"
    assert out.background_index == 1
    assert rows_of(out) == ["1111", "1001", "1001", "1111"]
    assert out.metadata.total_stitches == 4
    assert len({e.symbol for e in out.legend}) == 2


def test_pad_with_no_background_reuses_an_existing_winter_white_entry():
    p = pattern_from_rows(["01", "01"], background_index=None)  # index 0 already is 3865
    out = crop_pad.apply(p, crop_pad.Params(width=4, height=4, anchor="fit_content"))
    assert [e.dmc_color.code for e in out.legend] == ["3865", "310"]
    assert out.background_index == 0
    assert rows_of(out) == ["0000", "0010", "0010", "0000"]


def test_pad_dmc_overrides_the_fabric_colour_when_there_is_no_background():
    p = pattern_from_rows(["11", "11"], n_colours=2, background_index=None)
    out = crop_pad.apply(p, crop_pad.Params(width=4, height=4, anchor="center", pad_dmc="3799"))
    assert out.legend[out.background_index].dmc_color.code == "3799"
    with pytest.raises(OpError, match="9999"):
        crop_pad.apply(p, crop_pad.Params(width=4, height=4, pad_dmc="9999"))


def test_pad_dmc_is_ignored_when_the_pattern_already_has_a_background():
    out = crop_pad.apply(small_pattern(), crop_pad.Params(width=7, height=7, pad_dmc="3799"))
    assert [e.dmc_color.code for e in out.legend] == ["3865", "310", "3830"]
    assert out.background_index == 0


# --- outline_to_backstitch ---------------------------------------------------

RING_7 = [
    "0000000",
    "0111110",
    "0122210",
    "0122210",
    "0122210",
    "0111110",
    "0000000",
]
OUTER_RING = {Segment(1, 1, 6, 1), Segment(1, 6, 6, 6), Segment(1, 1, 1, 6), Segment(6, 1, 6, 6)}
INNER_RING = {Segment(2, 2, 5, 2), Segment(2, 5, 5, 5), Segment(2, 2, 2, 5), Segment(5, 2, 5, 5)}


def corner_degrees(segments) -> Counter:
    degrees: Counter = Counter()
    for s in segments:
        degrees[(s.x1, s.y1)] += 1
        degrees[(s.x2, s.y2)] += 1
    return degrees


def test_outline_ring_becomes_backstitch_and_dissolves_into_its_neighbours():
    p = pattern_from_rows(RING_7)
    out = outline_to_backstitch.apply(p, outline_to_backstitch.Params(outline_dmc="310"))
    # Corner ring cells see only white; edge ring cells see one white and one
    # terracotta (tie -> lower index, white). The block keeps its 3x3 shape.
    assert rows_of(out) == [
        "0000000",
        "0000000",
        "0011100",
        "0011100",
        "0011100",
        "0000000",
        "0000000",
    ]
    assert [e.dmc_color.code for e in out.legend] == ["3865", "3830"]
    assert out.background_index == 0
    assert set(out.backstitch) == OUTER_RING | INNER_RING
    assert all(d % 2 == 0 for d in corner_degrees(out.backstitch).values())
    assert rows_of(p) == RING_7


def test_outline_adds_to_existing_backstitch():
    p = pattern_from_rows(RING_7)
    p.backstitch = [Segment(0, 0, 7, 0), Segment(1, 1, 3, 1)]     # second overlaps the new top edge
    out = outline_to_backstitch.apply(p, outline_to_backstitch.Params(outline_dmc="310"))
    assert set(out.backstitch) == {Segment(0, 0, 7, 0)} | OUTER_RING | INNER_RING


def test_keep_cells_leaves_the_grid_and_legend_alone():
    p = pattern_from_rows(RING_7)
    out = outline_to_backstitch.apply(p, outline_to_backstitch.Params(outline_dmc="310", keep_cells=True))
    assert rows_of(out) == RING_7
    assert [e.dmc_color.code for e in out.legend] == ["3865", "310", "3830"]
    assert set(out.backstitch) == OUTER_RING | INNER_RING


def test_auto_picks_the_darkest_non_background_entry():
    # Background is black here, so auto must skip it and take terracotta (2)
    # over white; index 2 is what gets outlined.
    p = pattern_from_rows(RING_7, background_index=1)
    out = outline_to_backstitch.apply(p, outline_to_backstitch.Params())
    assert set(out.backstitch) == INNER_RING
    assert "3830" not in [e.dmc_color.code for e in out.legend]
    assert rows_of(out) == ["0000000", "0111110", "0111110", "0111110", "0111110", "0111110", "0000000"]
    assert out.legend[out.background_index].dmc_color.code == "310"


def test_majority_rule_lets_inner_cells_wait_for_the_next_pass():
    # 2-wide outline band: the inner band has no non-outline neighbour in pass
    # 1, then takes the colour its outer neighbours settled on in pass 2.
    rows = ["000000", "011110", "011110", "011110", "011110", "000000"]
    out = outline_to_backstitch.apply(pattern_from_rows(rows), outline_to_backstitch.Params(outline_dmc="310"))
    assert rows_of(out) == ["000000"] * 6
    assert set(out.backstitch) == {Segment(1, 1, 5, 1), Segment(1, 5, 5, 5), Segment(1, 1, 1, 5), Segment(5, 1, 5, 5)}


def test_all_outline_with_a_background_falls_back_to_the_background():
    p = pattern_from_rows(["11", "11"], background_index=0)
    out = outline_to_backstitch.apply(p, outline_to_backstitch.Params(outline_dmc="310"))
    assert rows_of(out) == ["00", "00"]
    assert [e.dmc_color.code for e in out.legend] == ["3865"] and out.background_index == 0


def test_all_outline_with_no_background_falls_back_to_the_first_other_entry():
    p = pattern_from_rows(["11", "11"], n_colours=3, background_index=None)
    out = outline_to_backstitch.apply(p, outline_to_backstitch.Params(outline_dmc="310"))
    assert rows_of(out) == ["00", "00"]
    assert [e.dmc_color.code for e in out.legend] == ["3865"]
    assert set(out.backstitch) == {Segment(0, 0, 2, 0), Segment(0, 2, 2, 2), Segment(0, 0, 0, 2), Segment(2, 0, 2, 2)}


def test_all_outline_with_a_single_entry_legend_is_an_op_error():
    p = pattern_from_rows(["00", "00"], background_index=None)
    with pytest.raises(OpError, match="only"):
        outline_to_backstitch.apply(p, outline_to_backstitch.Params(outline_dmc="3865"))


def test_outline_rejects_the_background_and_unknown_codes():
    with pytest.raises(OpError, match="background"):
        outline_to_backstitch.apply(small_pattern(), outline_to_backstitch.Params(outline_dmc="3865"))
    with pytest.raises(OpError, match="4444"):
        outline_to_backstitch.apply(small_pattern(), outline_to_backstitch.Params(outline_dmc="4444"))


# --- registry ----------------------------------------------------------------

def test_registry_lists_the_kit_ops_with_groups():
    entries = {e["name"]: (e["kind"], e["group"]) for e in registry.schemas()}
    assert entries["background_to_fabric"] == ("pattern", "kit")
    assert entries["substitute_colour"] == ("pattern", "kit")
    assert entries["merge_colours"] == ("pattern", "kit")
    assert entries["crop_pad"] == ("pattern", "kit")
    assert entries["outline_to_backstitch"] == ("pattern", "outline")
