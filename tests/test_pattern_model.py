"""Tests for the Pattern model: backstitch, background, recipe, lossless round-trip."""

import json
from pathlib import Path

import pytest

from xstitchlab.core.pattern import (
    Pattern,
    DMCColor,
    ColorLegendEntry,
    PatternMetadata,
    Segment,
    OpCall,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGNS = sorted(p for p in (REPO_ROOT / "designs").glob("0*/design.json"))


def make_pattern():
    legend = [
        ColorLegendEntry(DMCColor("3865", "Winter White", (249, 247, 241)), "●"),
        ColorLegendEntry(DMCColor("310", "Black", (0, 0, 0)), "■"),
    ]
    grid = [[0, 0, 1], [0, 1, 1], [1, 1, 1]]
    return Pattern(
        grid=grid,
        legend=legend,
        metadata=PatternMetadata(title="t"),
        backstitch=[Segment(0, 1, 2, 1)],
        background_index=0,
        recipe=[OpCall("pixelate", {"width": 3, "height": 3})],
    )


def test_round_trip_is_lossless():
    p = make_pattern()
    d = p.to_dict()
    q = Pattern.from_dict(d)
    assert q.grid == p.grid
    assert [e.dmc_color.code for e in q.legend] == ["3865", "310"]
    assert q.backstitch == [Segment(0, 1, 2, 1)]
    assert q.background_index == 0
    assert q.recipe == [OpCall("pixelate", {"width": 3, "height": 3})]
    assert q.to_dict() == d


def test_to_dict_derives_counts_and_excludes_background():
    d = make_pattern().to_dict()
    assert d["metadata"]["width"] == 3 and d["metadata"]["height"] == 3
    assert d["legend"][0]["stitch_count"] == 3
    assert d["legend"][1]["stitch_count"] == 6
    assert d["metadata"]["total_stitches"] == 6  # background excluded
    assert d["metadata"]["color_count"] == 2
    assert d["background_index"] == 0
    assert d["backstitch"] == [{"start": [0, 1], "end": [2, 1]}]
    assert d["recipe"] == [{"op": "pixelate", "params": {"width": 3, "height": 3}}]
    assert "backstitch_segments" not in d and "pipeline_stages" not in d


def test_stale_stitch_counts_in_input_are_ignored():
    d = make_pattern().to_dict()
    d["legend"][1]["stitch_count"] = 999
    assert Pattern.from_dict(d).to_dict()["legend"][1]["stitch_count"] == 6


def _heuristic_background_index(legend: list[dict]) -> int:
    """Legacy rule: pure white if present, else the brightest legend entry."""
    for idx, entry in enumerate(legend):
        if tuple(entry["rgb"]) == (255, 255, 255):
            return idx
    return max(
        range(len(legend)),
        key=lambda i: 0.299 * legend[i]["rgb"][0]
        + 0.587 * legend[i]["rgb"][1]
        + 0.114 * legend[i]["rgb"][2],
    )


@pytest.mark.parametrize("path", DESIGNS, ids=[p.parent.name for p in DESIGNS])
def test_committed_designs_are_canonical_and_lossless(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    p = Pattern.from_dict(raw)
    assert set(raw) == {"metadata", "legend", "grid", "backstitch", "background_index", "recipe"}
    assert p.recipe and p.background_index is not None
    assert p.to_dict() == raw  # counts, totals and title are exactly what the grid derives

    # Recount the grid ourselves, excluding the background, so the expectation
    # does not depend on the model under test.
    counts: dict[int, int] = {}
    for row in raw["grid"]:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    assert raw["metadata"]["total_stitches"] == sum(c for i, c in counts.items() if i != raw["background_index"])


def test_legacy_design_shape_loads_and_derives_totals():
    """Pre-recipe design files: backstitch_segments, background_color_index (or none), stale counts."""
    legend = [
        {"symbol": "●", "dmc_code": "3756", "dmc_name": "Baby Blue", "rgb": [238, 252, 252], "stitch_count": 999},
        {"symbol": "■", "dmc_code": "310", "dmc_name": "Black", "rgb": [0, 0, 0], "stitch_count": 999},
    ]
    grid = [[0, 0, 1], [0, 1, 1], [1, 1, 1]]
    segments = [{"start": [0, 1], "end": [2, 1]}, {"start": [1, 0], "end": [1, 3]}]
    legacy = {
        "id": "x", "metadata": {"title": "t", "total_stitches": 999}, "legend": legend, "grid": grid,
        "backstitch_segments": segments, "pipeline_stages": {}, "adjustment_stats": {},
    }
    p = Pattern.from_dict(legacy)
    assert len(p.backstitch) == 2
    assert p.background_index == _heuristic_background_index(legend) == 0
    d = p.to_dict()
    assert d["metadata"]["total_stitches"] == 6 and d["legend"][0]["stitch_count"] == 3
    assert "backstitch_segments" not in d and "pipeline_stages" not in d and "id" not in d

    legacy["background_color_index"] = 1
    assert Pattern.from_dict(legacy).background_index == 1


def test_segment_from_legacy_and_short_forms():
    assert Segment.from_dict({"start": [1, 2], "end": [3, 2]}) == Segment(1, 2, 3, 2)
    assert Segment.from_dict({"x1": 1, "y1": 2, "x2": 3, "y2": 2}) == Segment(1, 2, 3, 2)


def test_from_dict_tolerates_null_backstitch_and_recipe():
    d = make_pattern().to_dict()
    d["backstitch"] = None
    d["recipe"] = None
    p = Pattern.from_dict(d)
    assert p.backstitch == [] and p.recipe == []
    legacy = {"grid": d["grid"], "legend": d["legend"], "backstitch_segments": None}
    assert Pattern.from_dict(legacy).backstitch == []
