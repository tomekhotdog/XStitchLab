"""Benchmark tool: scoring a candidate pattern against a design's committed final."""

import json
from pathlib import Path

import pytest

from tests.ops.helpers import small_pattern
from tools import benchmark
from xstitchlab.core.pattern import Pattern
from xstitchlab.ops.base import OpError
from xstitchlab.ops.defaults import default_recipe

RIGA = Path("designs/01-three-brothers-riga")


def test_score_of_pattern_against_itself_is_perfect():
    p = small_pattern()
    s = benchmark.score(p, p)
    assert s == {"exact": 1.0, "size_ok": True, "confusion": {}, "diff_cells": 0}


def test_score_counts_one_changed_cell_on_a_5x5_grid():
    final = small_pattern()
    cand = final.copy()
    cand.grid[2][2] = 1                     # terra cotta centre -> black
    s = benchmark.score(cand, final)
    assert s["exact"] == pytest.approx(0.96)
    assert s["size_ok"] is True
    assert s["diff_cells"] == 1
    assert s["confusion"] == {("310", "3830"): 1}


def test_score_size_mismatch():
    final = small_pattern()
    cand = Pattern(grid=[[0, 0], [0, 0]], legend=final.legend)
    s = benchmark.score(cand, final)
    assert s == {"exact": 0.0, "size_ok": False, "confusion": {}, "diff_cells": None}


def test_benchmark_design_without_recipe_raises(tmp_path):
    (tmp_path / "input.png").write_bytes((RIGA / "input.png").read_bytes())
    stripped = json.loads((RIGA / "design.json").read_text(encoding="utf-8"))
    del stripped["recipe"]
    (tmp_path / "design.json").write_text(json.dumps(stripped), encoding="utf-8")
    with pytest.raises(OpError, match="recipe"):
        benchmark.benchmark_design(tmp_path)


@pytest.mark.slow
def test_benchmark_design_riga_with_predesigned_default():
    result = benchmark.benchmark_design(RIGA, default_recipe("predesigned", width=45))
    assert result["slug"] == "01-three-brothers-riga"
    assert result["size_ok"] is True
    assert result["cand_size"] == result["final_size"] == (45, 45)
    assert 0 < result["exact"] <= 1
    assert result["colors_final"] == 8 and result["backstitch_final"] == 212
    assert isinstance(result["candidate"], Pattern) and isinstance(result["final"], Pattern)
    assert all(len(row) == 3 for row in result["confusion"]) and len(result["confusion"]) <= 10


def test_score_treats_fabric_as_fabric_whatever_white_is_named():
    from xstitchlab.core.pattern import DMCColor
    a = small_pattern()
    b = small_pattern()
    b.legend[0].dmc_color = DMCColor("White", "White", (255, 255, 255))  # final names fabric differently
    assert benchmark.score(a, b)["exact"] == 1.0
    a.background_index = None  # candidate stitches the sky: now a real mismatch on 16 border cells
    assert benchmark.score(a, b)["exact"] == 9 / 25
