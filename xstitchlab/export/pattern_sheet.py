"""Branded printable Pattern Sheets (HTML, print to PDF from Chrome).

Two layouts from one Pattern: `a4` landscape (story, colour key and stitch
guide beside the chart, the layout the kits ship with) and `a5` portrait
(chart over legend, from `pattern_sheet_a5.html`). Background cells come from
`pattern.background_index`, the outline from `pattern.backstitch`.
"""

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from xstitchlab.core.pattern import Pattern, Segment

Layout = Literal["a4", "a5"]

# Print-safe symbols (ASCII that renders reliably at 3-4 pt).
SYMBOLS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J",
    "K", "L", "M", "N", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z",
    "a", "b", "c", "d", "e", "f", "g", "h", "j",
    "k", "m", "n", "p", "q", "r", "s", "t", "u",
    "v", "w", "x", "y", "z",
    "2", "3", "4", "5", "6", "7", "8", "9",
]

# Chart area per layout, in mm: (max width, max height). Cells are 1.5-4 mm.
_CHART_MM = {"a4": (125, 180), "a5": (126, 140)}
_A5_TEMPLATE = Path(__file__).with_name("pattern_sheet_a5.html")


def generate_pattern_sheet(
    pattern: Pattern,
    *,
    layout: Layout = "a4",
    title: str,
    history: str = "",
    output_path: Path,
) -> Path:
    """Write the sheet for `pattern` to `output_path` and return it."""
    if layout not in _CHART_MM:
        raise ValueError(f"unknown layout {layout!r} (choose from {sorted(_CHART_MM)})")
    sheet = _Sheet.from_pattern(pattern, title)
    cell_mm = _cell_mm(sheet, *_CHART_MM[layout])
    render = _render_a4 if layout == "a4" else _render_a5
    output_path = Path(output_path)
    output_path.write_text(render(sheet, cell_mm, html.escape(history, quote=False)))
    return output_path


# --- shared pieces -----------------------------------------------------------

@dataclass
class _Sheet:
    title: str
    grid: list[list[int]]
    legend: list[dict]        # {rgb, code, name, count}
    background: int | None
    backstitch: list[Segment]
    total_stitches: int
    difficulty: str
    width: int
    height: int

    @classmethod
    def from_pattern(cls, pattern: Pattern, title: str) -> "_Sheet":
        pattern.count_stitches()
        return cls(
            title=html.escape(title, quote=False),
            grid=pattern.grid,
            legend=[
                {"rgb": tuple(e.dmc_color.rgb), "code": e.dmc_color.code,
                 "name": e.dmc_color.name, "count": e.stitch_count}
                for e in pattern.legend
            ],
            background=pattern.background_index,
            backstitch=list(pattern.backstitch),
            total_stitches=pattern.metadata.total_stitches,
            difficulty=pattern.metadata.difficulty.capitalize(),
            width=pattern.width,
            height=pattern.height,
        )

    def symbol(self, index: int) -> str:
        return SYMBOLS[index] if index < len(SYMBOLS) else str(index)

    @property
    def backstitch_units(self) -> int:
        return sum(max(abs(s.x2 - s.x1), abs(s.y2 - s.y1)) for s in self.backstitch)


def _cell_mm(sheet: _Sheet, max_w: float, max_h: float) -> float:
    cell = min(max_w / sheet.width, max_h / sheet.height)
    cell = math.floor(cell * 10) / 10
    return max(1.5, min(cell, 4.0))


def _text_contrast_color(rgb) -> str:
    r, g, b = rgb
    return "#000" if 0.299 * r + 0.587 * g + 0.114 * b > 140 else "#fff"


def _grid_html(sheet: _Sheet) -> str:
    rows = []
    for y, row in enumerate(sheet.grid):
        cells = []
        for x, idx in enumerate(row):
            classes = []
            if x % 10 == 0:
                classes.append("col-major")
            if y % 10 == 0:
                classes.append("row-major")
            cls_attr = f' class="{" ".join(classes)}"' if classes else ""
            entry = sheet.legend[idx] if 0 <= idx < len(sheet.legend) else None
            if entry and idx != sheet.background:
                r, g, b = entry["rgb"]
                fg = _text_contrast_color(entry["rgb"])
                cells.append(f'<td{cls_attr} style="background:rgb({r},{g},{b});color:{fg}">{sheet.symbol(idx)}</td>')
            else:
                cells.append(f"<td{cls_attr}></td>")
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return f'<table class="grid-table">{"".join(rows)}</table>'


def _col_numbers(sheet: _Sheet, cell_size: str) -> str:
    spans = "".join(
        f'<span style="width:{cell_size};display:inline-block;text-align:right">{x if x % 10 == 0 else ""}</span>'
        for x in range(sheet.width)
    )
    return f'<div class="grid-numbers-top" style="margin-left:-{cell_size}">{spans}</div>'


def _row_numbers(sheet: _Sheet, cell_size: str) -> str:
    spans = "".join(
        f'<span style="height:{cell_size};justify-content:flex-end">{y if y % 10 == 0 else ""}</span>'
        for y in range(sheet.height)
    )
    return f'<div class="grid-numbers-left">{spans}</div>'


def _backstitch_svg(sheet: _Sheet, cell_mm: float) -> str:
    if not sheet.backstitch:
        return ""
    svg_w, svg_h = sheet.width * cell_mm, sheet.height * cell_mm
    lines = "".join(
        f'<line x1="{s.x1 * cell_mm}" y1="{s.y1 * cell_mm}" '
        f'x2="{s.x2 * cell_mm}" y2="{s.y2 * cell_mm}" '
        f'stroke="#1a1a1a" stroke-width="0.3" stroke-linecap="round"/>'
        for s in sheet.backstitch
    )
    return (
        f'<svg class="backstitch-overlay" width="{svg_w}mm" height="{svg_h}mm" '
        f'viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg">'
        f'{lines}</svg>'
    )


def _legend_html(sheet: _Sheet, *, background_row: bool) -> str:
    """Colour key; the A5 sheet lists the fabric colour as a "background" row, the A4 omits it."""
    rows = []
    for i, entry in enumerate(sheet.legend):
        r, g, b = entry["rgb"]
        swatch = f'<td><span class="legend-swatch" style="background:rgb({r},{g},{b})"></span></td>'
        if i == sheet.background:
            if background_row:
                rows.append(
                    f"<tr>{swatch}"
                    f'<td class="legend-symbol">—</td>'
                    f'<td class="legend-dmc">{entry["code"]}</td>'
                    f'<td class="legend-name">{entry["name"]}</td>'
                    f'<td class="legend-count legend-bg-note">background</td>'
                    f"</tr>"
                )
            continue
        rows.append(
            f"<tr>{swatch}"
            f'<td class="legend-symbol">{sheet.symbol(i)}</td>'
            f'<td class="legend-dmc">{entry["code"]}</td>'
            f'<td class="legend-name">{entry["name"]}</td>'
            f'<td class="legend-count">{entry["count"]:,}</td>'
            f"</tr>"
        )
    if sheet.backstitch:
        rows.append(
            f'<tr><td><span class="legend-swatch" style="background:#1a1a1a"></span></td>'
            f'<td class="legend-symbol">—</td><td class="legend-dmc">310</td>'
            f'<td class="legend-name">Backstitch (1 strand)</td>'
            f'<td class="legend-count">{sheet.backstitch_units} segs</td></tr>'
        )
    return (
        f'<table class="legend-table"><thead><tr>'
        f"<th></th><th>Sym</th><th>DMC</th><th>Colour</th><th style='text-align:right'>Stitches</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def _chart_parts(sheet: _Sheet, cell_mm: float) -> dict:
    cell_size = f"{cell_mm}mm"
    return {
        "cell_size": cell_size,
        "symbol_font_size": f"{max(3.5, cell_mm * 0.6):.1f}pt",
        "grid_html": _grid_html(sheet),
        "col_numbers": _col_numbers(sheet, cell_size),
        "row_numbers": _row_numbers(sheet, cell_size),
        "backstitch_svg": _backstitch_svg(sheet, cell_mm),
    }


# --- A5 --------------------------------------------------------------------------

def _render_a5(sheet: _Sheet, cell_mm: float, history: str) -> str:
    parts = _chart_parts(sheet, cell_mm)
    replacements = {
        "{{ title }}": sheet.title,
        "{{ cell_size }}": parts["cell_size"],
        "{{ symbol_font_size }}": parts["symbol_font_size"],
        "{{ col_numbers }}": parts["col_numbers"],
        "{{ row_numbers }}": parts["row_numbers"],
        "{{ grid_html }}": parts["grid_html"],
        "{{ backstitch_svg }}": parts["backstitch_svg"],
        "{{ legend_html }}": _legend_html(sheet, background_row=True),
        "{{ stitch_count }}": f"{sheet.total_stitches:,}",
        "{{ difficulty }}": sheet.difficulty,
        "{{ color_count }}": str(len(sheet.legend)),
        "{{ grid_width }}": str(sheet.width),
        "{{ grid_height }}": str(sheet.height),
    }
    page = _A5_TEMPLATE.read_text()
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


# --- A4 --------------------------------------------------------------------------

GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&'
    'family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&'
    'family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">'
)

COMMON_CSS = """
    :root {
        --sage: #9EA383;
        --beige: #D4B896;
        --terracotta: #C17B5F;
        --coffee: #3E2B1E;
        --cream: #F5F0E8;
        --warm-white: #FAF8F4;
        --stone: #B8AFA4;
        --ink: #2C2420;
    }
    @page { size: A4 landscape; margin: 0; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body {
        width: 297mm; height: 210mm;
        font-family: 'Barlow', sans-serif;
        font-size: 8pt; color: var(--ink);
        background: white; overflow: hidden;
    }
    .grid-table { border-collapse: collapse; line-height: 1; }
    .grid-table td {
        text-align: center; vertical-align: middle;
        font-family: 'Barlow', sans-serif; font-weight: 600;
        line-height: 1; padding: 0;
        border: 0.1mm solid rgba(0,0,0,0.08);
    }
    .grid-table td.col-major { border-left: 0.3mm solid rgba(0,0,0,0.25); }
    .grid-table td.row-major { border-top: 0.3mm solid rgba(0,0,0,0.25); }
    .grid-numbers-top {
        display: flex; font-size: 4.5pt;
        color: var(--stone); font-weight: 500;
    }
    .grid-numbers-top span { text-align: center; }
    .grid-numbers-left {
        position: absolute; left: -5.5mm; top: 0;
        font-size: 4.5pt; color: var(--stone); font-weight: 500;
        display: flex; flex-direction: column;
    }
    .grid-numbers-left span {
        text-align: right; display: flex;
        align-items: center; justify-content: flex-end;
    }
    .backstitch-overlay { position: absolute; top: 0; left: 0; pointer-events: none; }
    .legend-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
    .legend-table th {
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
        color: var(--stone); font-size: 6.5pt; padding: 0.5mm 1mm;
        text-align: left; border-bottom: 0.2mm solid var(--beige);
    }
    .legend-table td { padding: 0.6mm 1mm; vertical-align: middle; }
    .legend-swatch {
        width: 3.5mm; height: 3.5mm; border: 0.2mm solid rgba(0,0,0,0.15);
        display: inline-block; vertical-align: middle;
    }
    .legend-symbol { font-weight: 600; font-size: 8pt; text-align: center; white-space: nowrap; }
    .legend-dmc { font-weight: 500; color: var(--coffee); white-space: nowrap; }
    .legend-name { color: var(--ink); }
    .legend-count { text-align: right; color: var(--ink); font-weight: 500; white-space: nowrap; }
    .legend-bg-note { color: var(--stone); font-style: italic; font-size: 6.5pt; }
    @media print {
        html, body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
"""

STITCH_DIAGRAMS = """
<div class="stitch-guide">
    <h3>How to Stitch</h3>
    <div class="diagram-row">
        <div class="diagram-item">
            <div class="diagram-label">Cross Stitch</div>
            <svg viewBox="0 -10 120 69" class="diagram-svg">
                <!-- Fabric line -->
                <line x1="2" y1="24" x2="118" y2="24" stroke="#D4B896" stroke-width="0.4"/>

                <!-- 3 grid cells: each 18 wide, spaced at x=5, 23, 41 -->
                <rect x="5" y="6" width="18" height="18" fill="none" stroke="#D4B896" stroke-width="0.5"/>
                <rect x="23" y="6" width="18" height="18" fill="none" stroke="#D4B896" stroke-width="0.5"/>
                <rect x="41" y="6" width="18" height="18" fill="none" stroke="#D4B896" stroke-width="0.5"/>

                <!-- Step 1: up at bottom-left of cell 1 -->
                <circle cx="7" cy="22" r="1" fill="#C17B5F"/>
                <line x1="7" y1="32" x2="7" y2="23" stroke="#C17B5F" stroke-width="1" stroke-dasharray="1.5,1"/>
                <polygon points="5.5,24 7,21 8.5,24" fill="#C17B5F"/>
                <text x="7" y="37" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">1</text>

                <!-- Step 2: diagonal / across cell 1, down at top-right -->
                <line x1="7" y1="22" x2="21" y2="8" stroke="#C17B5F" stroke-width="1.3" stroke-linecap="round"/>
                <circle cx="21" cy="8" r="1" fill="#C17B5F"/>
                <text x="18" y="4" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">2</text>

                <!-- Step 3: up at bottom-left of cell 2 (= bottom-right of cell 1, via back) -->
                <line x1="21" y1="9" x2="21" y2="15" stroke="#B8AFA4" stroke-width="0.5" stroke-dasharray="1.5,1"/>
                <line x1="21" y1="15" x2="25" y2="15" stroke="#B8AFA4" stroke-width="0.5" stroke-dasharray="1.5,1"/>
                <line x1="25" y1="32" x2="25" y2="23" stroke="#C17B5F" stroke-width="1" stroke-dasharray="1.5,1"/>
                <polygon points="23.5,24 25,21 26.5,24" fill="#C17B5F"/>
                <circle cx="25" cy="22" r="1" fill="#C17B5F"/>
                <text x="25" y="37" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">3</text>

                <!-- Step 4: diagonal / across cell 2 -->
                <line x1="25" y1="22" x2="39" y2="8" stroke="#C17B5F" stroke-width="1.3" stroke-linecap="round"/>
                <circle cx="39" cy="8" r="1" fill="#C17B5F"/>
                <text x="36" y="4" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">4</text>

                <!-- Step 5: up at bottom-left of cell 3 -->
                <line x1="39" y1="9" x2="39" y2="15" stroke="#B8AFA4" stroke-width="0.5" stroke-dasharray="1.5,1"/>
                <line x1="39" y1="15" x2="43" y2="15" stroke="#B8AFA4" stroke-width="0.5" stroke-dasharray="1.5,1"/>
                <line x1="43" y1="32" x2="43" y2="23" stroke="#C17B5F" stroke-width="1" stroke-dasharray="1.5,1"/>
                <polygon points="41.5,24 43,21 44.5,24" fill="#C17B5F"/>
                <circle cx="43" cy="22" r="1" fill="#C17B5F"/>
                <text x="43" y="37" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">5</text>

                <!-- Step 6: diagonal / across cell 3 -->
                <line x1="43" y1="22" x2="57" y2="8" stroke="#C17B5F" stroke-width="1.3" stroke-linecap="round"/>
                <circle cx="57" cy="8" r="1" fill="#C17B5F"/>
                <text x="54" y="4" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">6</text>

                <!-- Arrow to return pass -->
                <line x1="62" y1="15" x2="68" y2="15" stroke="#B8AFA4" stroke-width="0.7"/>
                <polygon points="68,13 71,15 68,17" fill="#2C2420"/>
                <text x="66" y="11" text-anchor="middle" fill="#2C2420" font-size="3.5" font-family="Barlow">then</text>
                <text x="66" y="20" text-anchor="middle" fill="#2C2420" font-size="3.5" font-family="Barlow">return</text>

                <!-- Return pass: 3 cells with faded / and solid \\ -->
                <rect x="75" y="6" width="18" height="18" fill="none" stroke="#D4B896" stroke-width="0.5"/>
                <rect x="93" y="6" width="18" height="18" fill="none" stroke="#D4B896" stroke-width="0.5"/>
                <rect x="111" y="6" width="18" height="18" fill="none" stroke="#D4B896" stroke-width="0.5" opacity="0.5"/>

                <!-- Faded / strokes -->
                <line x1="77" y1="22" x2="91" y2="8" stroke="#C17B5F" stroke-width="1" stroke-linecap="round" opacity="0.3"/>
                <line x1="95" y1="22" x2="109" y2="8" stroke="#C17B5F" stroke-width="1" stroke-linecap="round" opacity="0.3"/>

                <!-- Step 7: \\ on cell 2 (rightmost completed first) -->
                <line x1="109" y1="22" x2="95" y2="8" stroke="#3E2B1E" stroke-width="1.3" stroke-linecap="round"/>
                <text x="102" y="4" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">7</text>

                <!-- Step 8: \\ on cell 1 -->
                <line x1="91" y1="22" x2="77" y2="8" stroke="#3E2B1E" stroke-width="1.3" stroke-linecap="round"/>
                <text x="84" y="4" text-anchor="middle" fill="#C17B5F" font-size="5" font-weight="600" font-family="Barlow">8</text>

                <!-- Direction arrows -->
                <line x1="108" y1="28" x2="80" y2="28" stroke="#B8AFA4" stroke-width="0.5"/>
                <polygon points="80,26.5 77,28 80,29.5" fill="#2C2420"/>
                <text x="94" y="33" text-anchor="middle" fill="#2C2420" font-size="3.5" font-family="Barlow">complete × right to left</text>

                <!-- Summary -->
                <text x="60" y="50" text-anchor="middle" fill="#2C2420" font-size="5" font-family="Barlow">Top stitch (/) always in the same direction</text>
            </svg>
            <div class="diagram-note">Work rows of half stitches (/) then return to complete each cross (\\)</div>
        </div>
        <div class="diagram-item">
            <div class="diagram-label">Backstitch</div>
            <svg viewBox="0 0 120 69" class="diagram-svg">
                <!-- Fabric cross-section: top line = front, dotted = back -->
                <line x1="5" y1="20" x2="115" y2="20" stroke="#D4B896" stroke-width="0.4"/>

                <!-- Grid edge markers on front -->
                <line x1="15" y1="17" x2="15" y2="23" stroke="#D4B896" stroke-width="0.5"/>
                <line x1="35" y1="17" x2="35" y2="23" stroke="#D4B896" stroke-width="0.5"/>
                <line x1="55" y1="17" x2="55" y2="23" stroke="#D4B896" stroke-width="0.5"/>
                <line x1="75" y1="17" x2="75" y2="23" stroke="#D4B896" stroke-width="0.5"/>
                <line x1="95" y1="17" x2="95" y2="23" stroke="#D4B896" stroke-width="0.5"/>

                <!-- Grid edge labels -->
                <text x="15" y="15" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">A</text>
                <text x="35" y="15" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">B</text>
                <text x="55" y="15" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">C</text>
                <text x="75" y="15" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">D</text>
                <text x="95" y="15" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">E</text>

                <!-- Step 1: needle comes up at B (from back to front) -->
                <line x1="35" y1="30" x2="35" y2="21" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1"/>
                <polygon points="33,22 35,19 37,22" fill="#C17B5F"/>
                <circle cx="35" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="35" y="36" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">1</text>
                <text x="35" y="42" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">up at B</text>

                <!-- Step 2: needle goes down at A (front to back — one edge back) -->
                <line x1="35" y1="19" x2="15" y2="19" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
                <line x1="15" y1="21" x2="15" y2="30" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1"/>
                <polygon points="13,28 15,31 17,28" fill="#C17B5F"/>
                <circle cx="15" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="15" y="36" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">2</text>
                <text x="15" y="42" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">down at A</text>

                <!-- Step 3: needle comes up at C (from back, skip one ahead) -->
                <line x1="15" y1="30" x2="55" y2="30" stroke="#B8AFA4" stroke-width="0.6" stroke-dasharray="2,1.5"/>
                <line x1="55" y1="30" x2="55" y2="21" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1"/>
                <polygon points="53,22 55,19 57,22" fill="#C17B5F"/>
                <circle cx="55" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="55" y="36" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">3</text>
                <text x="55" y="42" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">up at C</text>

                <!-- Step 4: needle goes down at B (back one edge) -->
                <line x1="55" y1="19" x2="35" y2="19" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="35" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="45" y="8" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">4</text>
                <text x="45" y="12" text-anchor="middle" fill="#2C2420" font-size="4" font-family="Barlow">down at B</text>

                <!-- Step 5: up at D, down at C (continue pattern) -->
                <line x1="75" y1="30" x2="75" y2="21" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1" opacity="0.5"/>
                <line x1="75" y1="19" x2="55" y2="19" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
                <text x="75" y="36" text-anchor="middle" fill="#C17B5F" font-size="5" font-family="Barlow" opacity="0.5">5…</text>

                <!-- Result label -->
                <text x="60" y="60" text-anchor="middle" fill="#2C2420" font-size="5" font-family="Barlow">Repeat: up ahead → down one edge back</text>
            </svg>
            <div class="diagram-note">Use 1 strand of DMC 310 — follow the black lines on the chart</div>
        </div>
    </div>
</div>
"""


def _render_a4(sheet: _Sheet, cell_mm: float, history: str) -> str:
    """A4 landscape: chart on the right, brand / story / colour key / stitch guide on the left."""
    p = _chart_parts(sheet, cell_mm)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{sheet.title} — Pattern Sheet</title>
{GOOGLE_FONTS}
<style>
{COMMON_CSS}
    .page {{
        width: 297mm; height: 210mm;
        padding: 7mm 8mm;
        display: flex; flex-direction: row; gap: 6mm;
    }}
    /* Left: info panel */
    .info-panel {{
        flex: 1; display: flex; flex-direction: column;
        gap: 2.5mm; overflow: hidden;
    }}
    /* Right: grid panel */
    .grid-panel {{
        flex: 1;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
    }}
    .grid-container {{ position: relative; line-height: 0; }}
    .grid-table td {{
        width: {p["cell_size"]}; height: {p["cell_size"]};
        font-size: {p["symbol_font_size"]};
    }}
    .brand-header {{
        text-align: center; padding-bottom: 2.5mm;
        border-bottom: 0.3mm solid var(--beige);
    }}
    .brand {{ font-family: 'Cinzel Decorative', serif; font-size: 11pt; color: var(--coffee); letter-spacing: 0.15em; }}
    .collection {{ font-family: 'Cinzel Decorative', serif; font-size: 7.5pt; color: var(--terracotta); letter-spacing: 0.12em; text-transform: uppercase; margin-top: 1mm; }}
    .tagline {{ font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 8pt; color: var(--stone); margin-top: 0.5mm; }}
    .design-title {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 13pt; color: var(--coffee); text-align: center;
        padding: 2mm 0;
    }}
    .story-legend-row {{
        display: flex; gap: 4mm;
        padding-top: 2mm; border-top: 0.3mm solid var(--beige);
    }}
    .history-section {{ font-size: 8.5pt; line-height: 1.6; color: var(--ink); flex: 1; text-align: justify; }}
    .history-section h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 8pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm;
    }}
    .legend-section {{
        flex: 1;
    }}
    .legend-section h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 8pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm;
    }}
    .stitch-guide {{
        padding-top: 2mm; border-top: 0.3mm solid var(--beige);
    }}
    .stitch-guide h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 7pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 2mm;
    }}
    .diagram-row {{
        display: flex; gap: 3mm;
    }}
    .diagram-item {{
        flex: 1;
        display: flex; flex-direction: column;
    }}
    .diagram-item .diagram-svg {{
        flex: 1;
    }}
    .diagram-label {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 8pt; color: var(--coffee); margin-bottom: 1mm;
    }}
    .diagram-svg {{
        width: 100%; height: auto;
        display: block; margin-bottom: 1mm;
    }}
    .diagram-note {{
        font-size: 6.5pt; color: var(--ink); line-height: 1.4;
    }}
    .footer-meta {{
        margin-top: auto; padding-top: 1.5mm;
        border-top: 0.2mm solid var(--beige);
        font-size: 6.5pt; color: var(--stone); text-align: center;
    }}
    .footer-meta span {{ margin: 0 1mm; }}
    .footer-brand {{
        font-family: 'Cinzel Decorative', serif; font-size: 6pt;
        color: var(--beige); letter-spacing: 0.1em; text-align: center;
        margin-top: 1mm;
    }}
</style></head>
<body>
<div class="page">
    <div class="grid-panel">
        <div class="grid-container">
            {p["col_numbers"]}
            <div style="position: relative;">
                {p["row_numbers"]}
                {p["grid_html"]}
                {p["backstitch_svg"]}
            </div>
        </div>
    </div>
    <div class="info-panel">
        <div class="brand-header">
            <div class="brand">&times; XStitchLabs &times;</div>
            <div class="collection">Hanseatic Collection</div>
            <div class="tagline">Cross-stitch the cities of the Hansa</div>
        </div>
        <div class="design-title">{sheet.title}</div>
        <div class="story-legend-row">
            <div class="history-section">
                <h3>The Story</h3>
                {history}
            </div>
            <div class="legend-section">
                <h3>Colour Key</h3>
                {_legend_html(sheet, background_row=False)}
            </div>
        </div>
        {STITCH_DIAGRAMS}
        <div class="footer-meta">
            <span>{sheet.total_stitches:,} stitches</span>
            <span>&middot;</span>
            <span>{sheet.difficulty}</span>
            <span>&middot;</span>
            <span>{len(sheet.legend)} colours</span>
            <span>&middot;</span>
            <span>{sheet.width}&times;{sheet.height}</span>
        </div>
        <div class="footer-brand">&times; XStitchLabs &times;</div>
    </div>
</div>
</body></html>"""
