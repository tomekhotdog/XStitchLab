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
def test_legacy_designs_load_and_keep_totals(path):
    raw = json.loads(path.read_text())
    p = Pattern.from_dict(raw)
    d = p.to_dict()
    assert len(p.backstitch) == len(raw["backstitch_segments"])
    assert p.background_index is not None
    if "background_color_index" in raw:
        assert p.background_index == raw["background_color_index"]

    # Recount the raw grid ourselves, excluding the heuristic background, so the
    # expectation does not depend on the model under test.
    counts: dict[int, int] = {}
    for row in raw["grid"]:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    bg = raw.get("background_color_index", _heuristic_background_index(raw["legend"]))
    recount = sum(c for i, c in counts.items() if i != bg)

    committed = raw["metadata"]["total_stitches"]
    if committed == recount:
        assert d["metadata"]["total_stitches"] == committed
    else:
        # Some committed design.json files were hand-edited outside count_stitches(),
        # so their metadata.total_stitches (and legend stitch_counts) are stale.
        # The model derives totals from the grid, so compare against the recount.
        assert d["metadata"]["total_stitches"] == recount
    assert d["metadata"]["width"] == raw["metadata"]["width"]


def test_segment_from_legacy_and_short_forms():
    assert Segment.from_dict({"start": [1, 2], "end": [3, 2]}) == Segment(1, 2, 3, 2)
    assert Segment.from_dict({"x1": 1, "y1": 2, "x2": 3, "y2": 2}) == Segment(1, 2, 3, 2)
