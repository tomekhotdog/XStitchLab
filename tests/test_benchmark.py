"""Each Hanseatic design's own recipe must keep reproducing its committed final.

Thresholds are the tuned score minus 0.02 (see docs/plans/2026-09-26-benchmark-log.md);
a drop below one means an op or the pixelation changed behaviour, not that the
design needs re-tuning.
"""

from pathlib import Path

import pytest

from tools import benchmark

DESIGNS = Path(__file__).resolve().parent.parent / "designs"

THRESHOLDS = {
    "01-three-brothers-riga": 0.88,
    "02-holstentor-lubeck": 0.93,
    "03-bryggen-bergen": 0.87,
    "04-townhall-tallinn": 0.88,
    "05-artus-gdansk": 0.76,
}


@pytest.mark.slow
@pytest.mark.parametrize("slug", sorted(THRESHOLDS))
def test_design_recipe_reproduces_its_final(slug):
    result = benchmark.benchmark_design(DESIGNS / slug)      # design.json's own recipe
    assert result["size_ok"], f"{slug}: candidate {result['cand_size']} vs final {result['final_size']}"
    assert result["exact"] >= THRESHOLDS[slug], (
        f"{slug}: exact {result['exact']:.4f} < {THRESHOLDS[slug]}; top confusion {result['confusion'][:5]}"
    )
    if result["backstitch_final"] > 0:
        assert result["backstitch_candidate"] > 0, f"{slug}: final has backstitch but the recipe produced none"
