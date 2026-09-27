"""export.threads: kit-rule thread estimates with background and backstitch rows."""

import math

from xstitchlab.core.pattern import Segment
from xstitchlab.export import threads

from tests.ops.helpers import pattern_from_rows, small_pattern


def test_background_row_has_count_but_no_thread():
    rows = threads.estimate(small_pattern())
    bg = rows[0]
    assert bg["is_background"] and not bg["is_backstitch"]
    assert bg["stitch_count"] == 16
    assert (bg["meters"], bg["skeins"], bg["sections_60cm"]) == (0, 0, 0)


def test_rows_follow_legend_order_with_all_keys():
    rows = threads.estimate(small_pattern())
    assert [r["dmc_code"] for r in rows] == ["3865", "310", "3830"]
    expected = {"dmc_code", "name", "rgb", "stitch_count", "meters", "skeins",
                "skeins_decimal", "sections_60cm", "is_background", "is_backstitch"}
    assert all(set(r) == expected for r in rows)


def test_cross_stitch_uses_kit_rule_1_5cm_per_stitch_and_180cm_sections():
    p = pattern_from_rows(["1" * 47] + ["0" * 47], background_index=0)  # 47 stitches of colour 1
    row = threads.estimate(p)[1]
    assert row["stitch_count"] == 47
    assert row["meters"] == 0.71          # ceil(47 * 1.5 = 70.5) = 71 cm
    assert row["sections_60cm"] == 1      # ceil(71 / 180)
    assert row["skeins"] == 1 and row["skeins_decimal"] == round(0.71 / 8, 2)


def test_sections_round_up_at_the_180cm_boundary():
    p120 = pattern_from_rows(["1" * 120], background_index=None)   # 180 cm exactly
    p121 = pattern_from_rows(["1" * 121], background_index=None)   # 181.5 -> 182 cm
    assert threads.estimate(p120)[1]["sections_60cm"] == 1
    assert threads.estimate(p121)[1]["sections_60cm"] == 2


def test_backstitch_row_only_when_segments_exist():
    assert not any(r["is_backstitch"] for r in threads.estimate(small_pattern()))
    p = small_pattern()
    p.backstitch = [Segment(1, 1, 4, 1), Segment(1, 1, 1, 4)]  # 3 + 3 unit edges
    rows = threads.estimate(p)
    bs = rows[-1]
    assert bs["is_backstitch"] and not bs["is_background"]
    assert (bs["dmc_code"], bs["name"], bs["rgb"]) == ("310", "Black (Backstitch, 1 strand)", [0, 0, 0])
    assert bs["stitch_count"] == 6
    assert bs["meters"] == 0.06           # 1 cm per unit, 1 strand
    assert bs["sections_60cm"] == 1       # ceil(6 / 360)


def test_backstitch_sections_use_360cm_per_section():
    p = small_pattern()
    p.backstitch = [Segment(0, 0, 361, 0)]
    assert threads.estimate(p)[-1]["sections_60cm"] == 2


def test_finer_fabric_needs_less_thread():
    p = pattern_from_rows(["1" * 100], background_index=None)
    at_14 = threads.estimate(p, fabric_count=14)[1]["meters"]
    at_18 = threads.estimate(p, fabric_count=18)[1]["meters"]
    assert at_18 < at_14
    assert at_18 == math.ceil(100 * 1.5 * 14 / 18) / 100


def test_totals_count_cross_stitches_only_and_sum_thread():
    p = small_pattern()
    p.backstitch = [Segment(1, 1, 4, 1)]
    rows = threads.estimate(p)
    t = threads.totals(rows)
    assert t["stitches"] == 9                       # 8 black + 1 terra cotta, not the 16 fabric cells
    assert t["meters"] == round(sum(r["meters"] for r in rows), 2)
    assert t["sections_60cm"] == sum(r["sections_60cm"] for r in rows) == 3
    assert t["skeins"] == sum(r["skeins"] for r in rows)
