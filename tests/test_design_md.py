"""design_md.render on the five committed designs and on synthetic folders."""

import re
import shutil
from collections import Counter
from pathlib import Path

import pytest

from xstitchlab.core.pattern import Pattern, Segment
from xstitchlab.library import DesignFolder
from xstitchlab.library import design_md

from tests.ops.helpers import small_pattern

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGNS = sorted(p for p in (REPO_ROOT / "designs").glob("0*") if (p / "design.json").is_file())

THREAD_ROW = re.compile(r"^\| (?P<name>[^|]+?) \| (?P<code>[^|]+?) \| (?P<stitches>[^|]+?) \| (?P<thread>[^|]+?) \| (?P<sections>[^|]+?) \|$")


def thread_rows(markdown: str) -> list[dict]:
    """Colour rows of the thread table (header, separator and totals row excluded)."""
    body = markdown.split(design_md.THREAD_TABLE_HEADING, 1)[1]
    rows = []
    for line in body.splitlines():
        m = THREAD_ROW.match(line)
        if m and not m["name"].startswith("-") and m["name"] not in ("Colour", ""):
            rows.append(m.groupdict())
    return rows


@pytest.fixture(params=DESIGNS, ids=[p.name for p in DESIGNS])
def committed(request, tmp_path):
    """A scratch copy of one committed design folder (never writes into designs/)."""
    src = request.param
    shutil.copytree(src, tmp_path / src.name)
    return DesignFolder(tmp_path, src.name)


def test_stitches_column_matches_grid_recount(committed):
    pattern = committed.read_pattern()
    rendered = design_md.render(pattern, committed)
    counts = Counter(v for row in pattern.grid for v in row)
    expected = {
        e.dmc_color.code: counts[i]
        for i, e in enumerate(pattern.legend) if i != pattern.background_index
    }
    rows = thread_rows(rendered)
    colour_rows = [r for r in rows if not r["stitches"].endswith("segs") and not r["thread"].startswith("**")]
    assert {r["code"]: int(r["stitches"]) for r in colour_rows} == expected
    units = sum(max(abs(s.x2 - s.x1), abs(s.y2 - s.y1)) for s in pattern.backstitch)
    backstitch_rows = [r for r in rows if r["stitches"].endswith("segs")]
    assert [r["stitches"] for r in backstitch_rows] == ([f"{units} segs"] if units else [])


def test_heading_description_and_hand_written_tail_are_preserved(committed):
    original = committed.design_md_path.read_text()
    rendered = design_md.render(committed.read_pattern(), committed)
    heading, description, tail = design_md.split_existing(original)
    assert rendered.splitlines()[0] == heading
    assert description in rendered
    assert tail and tail.startswith("## Label Text")
    assert rendered.rstrip("\n").endswith(tail)
    assert rendered.count("## Label Text") == 1


def test_background_note_names_the_fabric_colour(committed):
    pattern = committed.read_pattern()
    bg = pattern.legend[pattern.background_index].dmc_color
    rendered = design_md.render(pattern, committed)
    assert f"*Note: DMC {bg.code} ({bg.name}) is the background colour and is not stitched.*" in rendered
    assert not any(r["code"] == bg.code and not r["stitches"].endswith("segs") for r in thread_rows(rendered))


def test_layout_of_a_fresh_design_without_existing_md(tmp_path):
    folder = DesignFolder(tmp_path, "new-one")
    folder.path.mkdir()
    pattern = small_pattern()
    pattern.metadata.title = "New One"
    pattern.backstitch = [Segment(1, 1, 4, 1)]
    rendered = design_md.render(pattern, folder)
    assert rendered == (
        "# New One\n"
        "\n"
        "| | |\n"
        "|---|---|\n"
        "| **Stitches** | 9 |\n"
        "| **Difficulty** | Easy |\n"
        "| **Colours** | 3 |\n"
        "| **Total thread** | 0.2m |\n"
        "\n"
        "## Thread Table\n"
        "\n"
        "| Colour | DMC | Stitches | Thread needed | 60cm sections per kit |\n"
        "|--------|-----|----------|---------------|----------------------|\n"
        "| Black | 310 | 8 | 12cm (2-strand) | 1 |\n"
        "| Terra Cotta | 3830 | 1 | 2cm (2-strand) | 1 |\n"
        "| Black (Backstitch, 1 strand) | 310 | 3 segs | 3cm (1-strand) | 1 |\n"
        "| | | | **Total sections per kit** | **3** |\n"
        "\n"
        "*Note: DMC 3865 (Winter White) is the background colour and is not stitched.*\n"
    )


def test_no_background_means_no_note(tmp_path):
    folder = DesignFolder(tmp_path, "x")
    folder.path.mkdir()
    pattern = small_pattern()
    pattern.background_index = None
    rendered = design_md.render(pattern, folder)
    assert "background colour" not in rendered
    assert "| Winter White | 3865 | 16 |" in rendered


def test_rerender_is_idempotent(committed):
    pattern = committed.read_pattern()
    committed.write_pattern(pattern)
    once = committed.design_md_path.read_text()
    committed.write_pattern(committed.read_pattern())
    assert committed.design_md_path.read_text() == once
