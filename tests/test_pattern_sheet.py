"""export.pattern_sheet: A4 and A5 HTML from a Pattern."""

import re

import pytest

from xstitchlab.core.pattern import Segment
from xstitchlab.export.pattern_sheet import generate_pattern_sheet

from tests.ops.helpers import small_pattern


def sheet(tmp_path, layout, **kwargs):
    p = small_pattern()
    p.backstitch = [Segment(1, 1, 4, 1), Segment(1, 1, 1, 4), Segment(4, 1, 4, 4)]
    kwargs.setdefault("title", "Tiny <Ring> & Dot")
    kwargs.setdefault("history", "Once upon a time.")
    out = generate_pattern_sheet(p, layout=layout, output_path=tmp_path / f"sheet_{layout}.html", **kwargs)
    return p, out.read_text()


def grid_cells(html: str) -> list[str]:
    table = re.search(r'<table class="grid-table">(.*?)</table>', html, re.S).group(1)
    return re.findall(r"<td[^>]*>.*?</td>", table)


def overlay_lines(html: str) -> list[str]:
    svg = re.search(r'<svg class="backstitch-overlay".*?</svg>', html, re.S).group(0)
    return re.findall(r"<line ", svg)


@pytest.mark.parametrize("layout", ["a4", "a5"])
def test_sheet_has_title_one_cell_per_grid_cell_and_one_line_per_segment(tmp_path, layout):
    pattern, html = sheet(tmp_path, layout)
    assert "Tiny &lt;Ring&gt; &amp; Dot" in html
    cells = grid_cells(html)
    assert len(cells) == pattern.width * pattern.height == 25
    assert len(overlay_lines(html)) == len(pattern.backstitch) == 3
    assert "9 stitches" in html  # background cells are not counted


@pytest.mark.parametrize("layout", ["a4", "a5"])
def test_background_cells_are_blank_and_stitched_cells_carry_symbols(tmp_path, layout):
    pattern, html = sheet(tmp_path, layout)
    cells = grid_cells(html)
    flat = [v for row in pattern.grid for v in row]
    for value, cell in zip(flat, cells):
        if value == pattern.background_index:
            assert "style=" not in cell and cell.endswith("></td>")
        else:
            assert "background:rgb(" in cell and cell[-6:-5] in "BC"  # symbols B, C for legend 1, 2


def test_layouts_differ_in_page_size_and_story(tmp_path):
    _, a4 = sheet(tmp_path, "a4")
    _, a5 = sheet(tmp_path, "a5")
    assert "size: A4 landscape" in a4 and "size: A5 portrait" in a5
    assert "Once upon a time." in a4 and "The Story" in a4
    assert "Once upon a time." not in a5


def test_legend_rows(tmp_path):
    _, a4 = sheet(tmp_path, "a4")
    _, a5 = sheet(tmp_path, "a5")
    assert "Backstitch (1 strand)" in a4 and "9 segs" in a4
    assert 'legend-bg-note">background' in a5     # A5 lists the fabric colour
    assert 'legend-bg-note">background' not in a4  # A4 omits it


def test_unknown_layout(tmp_path):
    with pytest.raises(ValueError):
        generate_pattern_sheet(small_pattern(), layout="letter", title="t", output_path=tmp_path / "x.html")
