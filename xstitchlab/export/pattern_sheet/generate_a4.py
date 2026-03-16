"""Generate A4 landscape pattern sheet variants from design JSON files."""

import json
import math
import sys
from pathlib import Path


SYMBOLS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J",
    "K", "L", "M", "N", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z",
    "a", "b", "c", "d", "e", "f", "g", "h", "j",
    "k", "m", "n", "p", "q", "r", "s", "t", "u",
    "v", "w", "x", "y", "z",
    "2", "3", "4", "5", "6", "7", "8", "9",
]

# Historical descriptions per design
HISTORY = {
    "riga": (
        "The Three Brothers are a complex of three medieval dwellings in "
        "the Old Town of Riga, Latvia. Dating from the 15th, 17th and late "
        "17th centuries respectively, they form the oldest residential "
        "building ensemble in the city. The houses at 17, 19 and 21 Mazā "
        "Pils iela each represent a distinct era of Riga's architectural "
        "evolution — from the earliest stone-built merchant houses, through "
        "the Dutch-influenced Renaissance, to the Baroque period. Together "
        "they tell the story of a Hanseatic trading city that prospered "
        "across three centuries of Baltic commerce."
    ),
    "bergen": (
        "Bryggen is the old wharf of Bergen, Norway — a row of colourful "
        "Hanseatic wooden warehouses lining the eastern shore of Vågen "
        "harbour. First built in the 12th century and rebuilt many times "
        "after fire, the surviving buildings date mostly from the 18th "
        "century but follow the original medieval plan. Bryggen was the "
        "centre of the Hanseatic League's trading empire in Norway, where "
        "German merchants exchanged grain and beer for stockfish. Today it "
        "is a UNESCO World Heritage Site and one of Norway's most iconic "
        "landmarks."
    ),
    "lubeck": (
        "The Holstentor is a late-Gothic city gate built in 1478, and the "
        "most recognisable symbol of Lübeck, Germany — once the 'Queen of "
        "the Hanse'. With its two round towers and arched central passage, "
        "the gate guarded the western approach to the city across the river "
        "Trave. Lübeck was the capital of the Hanseatic League for over "
        "three centuries, and the Holstentor's imposing brick facade still "
        "bears the Latin inscription 'Concordia Domi Foris Pax' — Harmony "
        "Within, Peace Without."
    ),
    "tallinn": (
        "Tallinn Town Hall is the only surviving Gothic town hall in "
        "Northern Europe, built between 1402 and 1404. Standing in "
        "Raekoja plats at the heart of Tallinn's medieval Old Town, its "
        "slender octagonal tower topped by the weathervane 'Old Thomas' "
        "has watched over the city for six centuries. Tallinn — then known "
        "as Reval — was a key Hanseatic port connecting the trade routes "
        "between Western Europe and Novgorod."
    ),
    "gdansk": (
        "Artus Court is a grand Gothic hall on the Long Market in Gdańsk, "
        "Poland — built in the 14th century as a meeting place for the "
        "city's merchants and named after the legendary King Arthur. Its "
        "ornate Renaissance facade, with tall arched windows and a stepped "
        "parapet, reflects the wealth of a city that was one of the "
        "Hanseatic League's most important Baltic ports. Inside, the Great "
        "Hall housed lavish banquets and civic gatherings beneath what was "
        "once the tallest brick vault in medieval Europe."
    ),
}


DISPLAY_TITLES = {
    "three-brothers-riga": "Three Brothers, Riga",
    "3_brothers_riga": "Three Brothers, Riga",
    "riga_3_brothers": "Three Brothers, Riga",
    "bryggen-bergen": "Bryggen, Bergen",
    "bergen_bryggen": "Bryggen, Bergen",
    "holstentor-lubeck": "Holstentor, Lübeck",
    "lubeck_holstentor": "Holstentor, Lübeck",
    "townhall-tallinn": "Town Hall, Tallinn",
    "tallinn_townhall": "Town Hall, Tallinn",
    "artus-gdansk": "Artus Court, Gdańsk",
    "gdansk_artus": "Artus Court, Gdańsk",
}


def get_display_title(design_path, metadata):
    """Return a display-friendly title, falling back to metadata."""
    path_str = str(Path(design_path)).lower()
    for key, title in DISPLAY_TITLES.items():
        if key in path_str:
            return title
    raw = metadata.get("title", "Untitled")
    return raw.replace("_", " ").title()


def text_contrast_color(rgb):
    r, g, b = rgb
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000" if luminance > 140 else "#fff"


def build_grid_data(data):
    """Extract and compute all grid/legend data from design JSON."""
    grid = data["grid"]
    legend = data["legend"]
    metadata = data["metadata"]
    backstitch = data.get("backstitch_segments", [])

    grid_h = len(grid)
    grid_w = len(grid[0]) if grid else 0

    # Background index
    bg_idx = None
    for i, entry in enumerate(legend):
        if entry["rgb"] == [255, 255, 255]:
            bg_idx = i
            break
    if bg_idx is None:
        max_bright = -1
        for i, entry in enumerate(legend):
            r, g, b = entry["rgb"]
            bright = 0.299 * r + 0.587 * g + 0.114 * b
            if bright > max_bright:
                max_bright = bright
                bg_idx = i

    # Symbol map
    sym_map = {}
    for i in range(len(legend)):
        sym_map[i] = SYMBOLS[i] if i < len(SYMBOLS) else str(i)

    # Recount stitches from grid (JSON stitch_count may be stale)
    from collections import Counter
    grid_counts = Counter()
    for row in grid:
        for idx in row:
            grid_counts[idx] += 1
    for i in range(len(legend)):
        legend[i]["stitch_count"] = grid_counts.get(i, 0)

    # Stitch count
    total_stitches = sum(
        grid_counts.get(i, 0)
        for i in range(len(legend))
        if i != bg_idx
    )

    # Backstitch unit count
    backstitch_unit_count = sum(
        max(abs(s["end"][0] - s["start"][0]), abs(s["end"][1] - s["start"][1]))
        for s in backstitch
    ) if backstitch else 0

    return {
        "grid": grid, "legend": legend, "metadata": metadata,
        "backstitch": backstitch, "grid_h": grid_h, "grid_w": grid_w,
        "bg_idx": bg_idx, "sym_map": sym_map, "total_stitches": total_stitches,
        "backstitch_unit_count": backstitch_unit_count,
    }


def build_grid_html(d, cell_mm):
    """Build the grid table HTML."""
    cell_size = f"{cell_mm}mm"
    symbol_font_size = f"{max(3.5, cell_mm * 0.6):.1f}pt"
    rows_html = []
    for y, row in enumerate(d["grid"]):
        cells = []
        for x, color_idx in enumerate(row):
            entry = d["legend"][color_idx] if 0 <= color_idx < len(d["legend"]) else None
            classes = []
            if x % 10 == 0:
                classes.append("col-major")
            if y % 10 == 0:
                classes.append("row-major")
            cls_attr = f' class="{" ".join(classes)}"' if classes else ""
            if entry and color_idx != d["bg_idx"]:
                r, g, b = entry["rgb"]
                fg = text_contrast_color(entry["rgb"])
                sym = d["sym_map"].get(color_idx, "?")
                cells.append(f'<td{cls_attr} style="background:rgb({r},{g},{b});color:{fg}">{sym}</td>')
            else:
                cells.append(f"<td{cls_attr}></td>")
        rows_html.append(f'<tr>{"".join(cells)}</tr>')
    return f'<table class="grid-table">{"".join(rows_html)}</table>', cell_size, symbol_font_size


def build_col_numbers(d, cell_size):
    spans = []
    for x in range(d["grid_w"]):
        label = str(x) if x % 10 == 0 else ""
        spans.append(f'<span style="width:{cell_size};display:inline-block;text-align:right">{label}</span>')
    return f'<div class="grid-numbers-top" style="margin-left:-{cell_size}">{"".join(spans)}</div>'


def build_row_numbers(d, cell_size):
    spans = []
    for y in range(d["grid_h"]):
        label = str(y) if y % 10 == 0 else ""
        spans.append(f'<span style="height:{cell_size};justify-content:flex-end">{label}</span>')
    return f'<div class="grid-numbers-left">{"".join(spans)}</div>'


def build_backstitch_svg(d, cell_mm):
    if not d["backstitch"]:
        return ""
    svg_w = d["grid_w"] * cell_mm
    svg_h = d["grid_h"] * cell_mm
    lines = []
    for seg in d["backstitch"]:
        sx, sy = seg["start"]
        ex, ey = seg["end"]
        lines.append(
            f'<line x1="{sx * cell_mm}" y1="{sy * cell_mm}" '
            f'x2="{ex * cell_mm}" y2="{ey * cell_mm}" '
            f'stroke="#1a1a1a" stroke-width="0.3" stroke-linecap="round"/>'
        )
    return (
        f'<svg class="backstitch-overlay" width="{svg_w}mm" height="{svg_h}mm" '
        f'viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(lines)}</svg>'
    )


def build_legend_html(d):
    rows = []
    for i, entry in enumerate(d["legend"]):
        r, g, b = entry["rgb"]
        sym = d["sym_map"].get(i, "?")
        dmc = entry.get("dmc_code", "?")
        name = entry.get("dmc_name", "Unknown")
        count = entry.get("stitch_count", 0)
        if i == d["bg_idx"]:
            continue
        else:
            rows.append(
                f'<tr><td><span class="legend-swatch" style="background:rgb({r},{g},{b})"></span></td>'
                f'<td class="legend-symbol">{sym}</td><td class="legend-dmc">{dmc}</td>'
                f'<td class="legend-name">{name}</td><td class="legend-count">{count:,}</td></tr>'
            )
    if d["backstitch"]:
        rows.append(
            f'<tr><td><span class="legend-swatch" style="background:#1a1a1a"></span></td>'
            f'<td class="legend-symbol">—</td><td class="legend-dmc">310</td>'
            f'<td class="legend-name">Backstitch (1 strand)</td>'
            f'<td class="legend-count">{d["backstitch_unit_count"]} segs</td></tr>'
        )
    return (
        f'<table class="legend-table"><thead><tr>'
        f"<th></th><th>Sym</th><th>DMC</th><th>Colour</th><th style='text-align:right'>Stitches</th>"
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def get_history(design_path):
    """Match a history blurb by design path."""
    path_str = str(Path(design_path)).lower()
    for key, text in HISTORY.items():
        if key in path_str:
            return text
    return "A design from the Hanseatic Collection by XStitchLabs."


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
                <polygon points="68,13 71,15 68,17" fill="#B8AFA4"/>
                <text x="66" y="11" text-anchor="middle" fill="#B8AFA4" font-size="3.5" font-family="Barlow">then</text>
                <text x="66" y="20" text-anchor="middle" fill="#B8AFA4" font-size="3.5" font-family="Barlow">return</text>

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
                <polygon points="80,26.5 77,28 80,29.5" fill="#B8AFA4"/>
                <text x="94" y="33" text-anchor="middle" fill="#B8AFA4" font-size="3.5" font-family="Barlow">complete × right to left</text>

                <!-- Summary -->
                <text x="60" y="50" text-anchor="middle" fill="#B8AFA4" font-size="5" font-family="Barlow">Top stitch (/) always in the same direction</text>
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
                <text x="15" y="15" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">A</text>
                <text x="35" y="15" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">B</text>
                <text x="55" y="15" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">C</text>
                <text x="75" y="15" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">D</text>
                <text x="95" y="15" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">E</text>

                <!-- Step 1: needle comes up at B (from back to front) -->
                <line x1="35" y1="30" x2="35" y2="21" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1"/>
                <polygon points="33,22 35,19 37,22" fill="#C17B5F"/>
                <circle cx="35" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="35" y="36" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">1</text>
                <text x="35" y="42" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">up at B</text>

                <!-- Step 2: needle goes down at A (front to back — one edge back) -->
                <line x1="35" y1="19" x2="15" y2="19" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
                <line x1="15" y1="21" x2="15" y2="30" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1"/>
                <polygon points="13,28 15,31 17,28" fill="#C17B5F"/>
                <circle cx="15" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="15" y="36" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">2</text>
                <text x="15" y="42" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">down at A</text>

                <!-- Step 3: needle comes up at C (from back, skip one ahead) -->
                <line x1="15" y1="30" x2="55" y2="30" stroke="#B8AFA4" stroke-width="0.6" stroke-dasharray="2,1.5"/>
                <line x1="55" y1="30" x2="55" y2="21" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1"/>
                <polygon points="53,22 55,19 57,22" fill="#C17B5F"/>
                <circle cx="55" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="55" y="36" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">3</text>
                <text x="55" y="42" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">up at C</text>

                <!-- Step 4: needle goes down at B (back one edge) -->
                <line x1="55" y1="19" x2="35" y2="19" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="35" cy="20" r="1.2" fill="#C17B5F"/>
                <text x="45" y="8" text-anchor="middle" fill="#C17B5F" font-size="6" font-weight="600" font-family="Barlow">4</text>
                <text x="45" y="12" text-anchor="middle" fill="#B8AFA4" font-size="4" font-family="Barlow">down at B</text>

                <!-- Step 5: up at D, down at C (continue pattern) -->
                <line x1="75" y1="30" x2="75" y2="21" stroke="#C17B5F" stroke-width="1.2" stroke-dasharray="1.5,1" opacity="0.5"/>
                <line x1="75" y1="19" x2="55" y2="19" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
                <text x="75" y="36" text-anchor="middle" fill="#C17B5F" font-size="5" font-family="Barlow" opacity="0.5">5…</text>

                <!-- Result label -->
                <text x="60" y="60" text-anchor="middle" fill="#B8AFA4" font-size="5" font-family="Barlow">Repeat: up ahead → down one edge back</text>
            </svg>
            <div class="diagram-note">Use 1 strand of DMC 310 — follow the black lines on the chart</div>
        </div>
    </div>
</div>
"""

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

GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&'
    'family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&'
    'family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">'
)


def generate_option_a(d, cell_mm, history, output_path, design_path=None):
    """Option A: Two-column 50/50 — info panel left, grid right."""
    grid_html, cell_size, symbol_font_size = build_grid_html(d, cell_mm)
    col_numbers = build_col_numbers(d, cell_size)
    row_numbers = build_row_numbers(d, cell_size)
    backstitch_svg = build_backstitch_svg(d, cell_mm)
    legend_html = build_legend_html(d)
    m = d["metadata"]
    title = get_display_title(design_path, m) if design_path else m.get("title", "Untitled")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{title} — Pattern Sheet</title>
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
        width: {cell_size}; height: {cell_size};
        font-size: {symbol_font_size};
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
        font-size: 6.5pt; color: var(--stone); line-height: 1.4;
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
            {col_numbers}
            <div style="position: relative;">
                {row_numbers}
                {grid_html}
                {backstitch_svg}
            </div>
        </div>
    </div>
    <div class="info-panel">
        <div class="brand-header">
            <div class="brand">&times; XStitchLabs &times;</div>
            <div class="collection">Hanseatic Collection</div>
            <div class="tagline">Cross-stitch the cities of the Hansa</div>
        </div>
        <div class="design-title">{title}</div>
        <div class="story-legend-row">
            <div class="history-section">
                <h3>The Story</h3>
                {history}
            </div>
            <div class="legend-section">
                <h3>Colour Key</h3>
                {legend_html}
            </div>
        </div>
        {STITCH_DIAGRAMS}
        <div class="footer-meta">
            <span>{d['total_stitches']:,} stitches</span>
            <span>&middot;</span>
            <span>{m.get('difficulty', 'Medium').capitalize()}</span>
            <span>&middot;</span>
            <span>{m.get('color_count', len(d['legend']))} colours</span>
            <span>&middot;</span>
            <span>{d['grid_w']}&times;{d['grid_h']}</span>
        </div>
        <div class="footer-brand">&times; XStitchLabs &times;</div>
    </div>
</div>
</body></html>"""

    Path(output_path).write_text(html)
    print(f"  Option A: {output_path}")


def generate_option_b(d, cell_mm, history, output_path):
    """Option B: Grid top-centre, bottom strip with legend + history + instructions in 3 columns."""
    grid_html, cell_size, symbol_font_size = build_grid_html(d, cell_mm)
    col_numbers = build_col_numbers(d, cell_size)
    row_numbers = build_row_numbers(d, cell_size)
    backstitch_svg = build_backstitch_svg(d, cell_mm)
    legend_html = build_legend_html(d)
    title = d["metadata"].get("title", "Untitled")
    m = d["metadata"]

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{title} — Pattern Sheet</title>
{GOOGLE_FONTS}
<style>
{COMMON_CSS}
    .page {{
        width: 297mm; height: 210mm;
        padding: 5mm 8mm;
        display: flex; flex-direction: column;
    }}
    /* Header bar */
    .header-bar {{
        display: flex; justify-content: space-between; align-items: baseline;
        padding-bottom: 2mm; border-bottom: 0.3mm solid var(--beige);
        flex-shrink: 0;
    }}
    .header-left {{ display: flex; align-items: baseline; gap: 3mm; }}
    .brand {{ font-family: 'Cinzel Decorative', serif; font-size: 8pt; color: var(--coffee); letter-spacing: 0.15em; }}
    .collection {{ font-family: 'Cinzel Decorative', serif; font-size: 5.5pt; color: var(--terracotta); letter-spacing: 0.1em; text-transform: uppercase; }}
    .design-title {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 10pt; color: var(--coffee);
    }}
    .header-meta {{ font-size: 5.5pt; color: var(--stone); }}
    .header-meta span {{ margin-left: 2mm; }}
    /* Grid area */
    .grid-section {{
        flex: 1; display: flex; align-items: center; justify-content: center;
        padding: 2mm 0; min-height: 0;
    }}
    .grid-container {{ position: relative; line-height: 0; }}
    .grid-table td {{
        width: {cell_size}; height: {cell_size};
        font-size: {symbol_font_size};
    }}
    /* Bottom strip */
    .bottom-strip {{
        flex-shrink: 0; display: flex; gap: 5mm;
        padding-top: 2.5mm; border-top: 0.3mm solid var(--beige);
    }}
    .bottom-col {{ flex: 1; overflow: hidden; }}
    .bottom-col h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 5.5pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm;
    }}
    .history-text {{ font-size: 6pt; line-height: 1.5; color: var(--ink); }}
    .instructions {{ font-size: 5.5pt; line-height: 1.45; }}
    .instructions h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 5.5pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm; margin-top: 2mm;
    }}
    .instruction-steps {{ display: flex; flex-direction: column; gap: 0.5mm; }}
    .step {{ display: flex; gap: 1mm; align-items: baseline; }}
    .step-num {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 7pt; color: var(--terracotta); flex-shrink: 0;
        width: 3mm; text-align: center;
    }}
    .step-text {{ color: var(--ink); }}
    .footer-brand {{
        font-family: 'Cinzel Decorative', serif; font-size: 6pt;
        color: var(--beige); letter-spacing: 0.1em; text-align: right;
        margin-top: 1.5mm;
    }}
</style></head>
<body>
<div class="page">
    <div class="header-bar">
        <div class="header-left">
            <div class="brand">&times; XStitchLabs &times;</div>
            <div class="collection">Hanseatic Collection</div>
        </div>
        <div class="design-title">{title}</div>
        <div class="header-meta">
            <span>{d['total_stitches']:,} stitches</span>
            <span>&middot;</span>
            <span>{m.get('difficulty', 'Medium').capitalize()}</span>
            <span>&middot;</span>
            <span>{m.get('color_count', len(d['legend']))} colours</span>
            <span>&middot;</span>
            <span>{d['grid_w']}&times;{d['grid_h']}</span>
        </div>
    </div>
    <div class="grid-section">
        <div class="grid-container">
            {col_numbers}
            <div style="position: relative;">
                {row_numbers}
                {grid_html}
                {backstitch_svg}
            </div>
        </div>
    </div>
    <div class="bottom-strip">
        <div class="bottom-col">
            <h3>Colour Key</h3>
            {legend_html}
        </div>
        <div class="bottom-col">
            <h3>The Story</h3>
            <div class="history-text">{history}</div>
        </div>
        <div class="bottom-col">
            {CROSS_STITCH_INSTRUCTIONS}
        </div>
    </div>
    <div class="footer-brand">&times; XStitchLabs &times;</div>
</div>
</body></html>"""

    Path(output_path).write_text(html)
    print(f"  Option B: {output_path}")


def generate_option_c(d, cell_mm, history, output_path):
    """Option C: Full-width header, grid left with legend below, history + instructions right."""
    grid_html, cell_size, symbol_font_size = build_grid_html(d, cell_mm)
    col_numbers = build_col_numbers(d, cell_size)
    row_numbers = build_row_numbers(d, cell_size)
    backstitch_svg = build_backstitch_svg(d, cell_mm)
    legend_html = build_legend_html(d)
    title = d["metadata"].get("title", "Untitled")
    m = d["metadata"]

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{title} — Pattern Sheet</title>
{GOOGLE_FONTS}
<style>
{COMMON_CSS}
    .page {{
        width: 297mm; height: 210mm;
        padding: 6mm 8mm 5mm 8mm;
        display: flex; flex-direction: column;
    }}
    /* Full-width branded header */
    .header {{
        display: flex; justify-content: space-between; align-items: center;
        padding-bottom: 3mm; margin-bottom: 3mm;
        border-bottom: 0.4mm solid var(--beige);
        flex-shrink: 0;
    }}
    .brand-block {{ text-align: left; }}
    .brand {{ font-family: 'Cinzel Decorative', serif; font-size: 10pt; color: var(--coffee); letter-spacing: 0.15em; }}
    .collection {{ font-family: 'Cinzel Decorative', serif; font-size: 5.5pt; color: var(--terracotta); letter-spacing: 0.1em; text-transform: uppercase; margin-top: 0.5mm; }}
    .title-block {{ text-align: center; }}
    .design-title {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 13pt; color: var(--coffee);
    }}
    .tagline {{
        font-family: 'Cormorant Garamond', serif; font-style: italic;
        font-size: 7pt; color: var(--stone); margin-top: 0.5mm;
    }}
    .stats-block {{ text-align: right; font-size: 6pt; color: var(--stone); line-height: 1.6; }}
    /* Main body: two columns */
    .body {{ display: flex; flex: 1; gap: 6mm; min-height: 0; }}
    /* Left column: grid + legend */
    .left-col {{ flex: 0 0 172mm; display: flex; flex-direction: column; }}
    .grid-area {{
        flex: 1; display: flex; align-items: center;
        justify-content: center; min-height: 0;
    }}
    .grid-container {{ position: relative; line-height: 0; }}
    .grid-table td {{
        width: {cell_size}; height: {cell_size};
        font-size: {symbol_font_size};
    }}
    .legend-area {{
        flex-shrink: 0; padding-top: 2mm;
        border-top: 0.2mm solid var(--beige);
    }}
    /* Right column: history + instructions */
    .right-col {{
        flex: 1; display: flex; flex-direction: column;
        gap: 3mm; overflow: hidden;
    }}
    .section-title {{
        font-family: 'Cinzel Decorative', serif; font-size: 6pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm;
    }}
    .history-text {{ font-size: 6.5pt; line-height: 1.55; color: var(--ink); }}
    .divider {{ border: none; border-top: 0.2mm solid var(--beige); margin: 1mm 0; }}
    .instructions {{ font-size: 6pt; line-height: 1.5; }}
    .instructions h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 6pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm; margin-top: 2.5mm;
    }}
    .instruction-steps {{ display: flex; flex-direction: column; gap: 0.8mm; }}
    .step {{ display: flex; gap: 1.5mm; align-items: baseline; }}
    .step-num {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 8pt; color: var(--terracotta); flex-shrink: 0;
        width: 3mm; text-align: center;
    }}
    .step-text {{ color: var(--ink); }}
    .right-footer {{
        margin-top: auto; padding-top: 1.5mm;
        border-top: 0.2mm solid var(--beige);
        text-align: center;
    }}
    .footer-brand {{
        font-family: 'Cinzel Decorative', serif; font-size: 6pt;
        color: var(--beige); letter-spacing: 0.1em;
    }}
</style></head>
<body>
<div class="page">
    <div class="header">
        <div class="brand-block">
            <div class="brand">&times; XStitchLabs &times;</div>
            <div class="collection">Hanseatic Collection</div>
        </div>
        <div class="title-block">
            <div class="design-title">{title}</div>
            <div class="tagline">Cross-stitch the cities of the Hansa</div>
        </div>
        <div class="stats-block">
            {d['total_stitches']:,} stitches<br>
            {m.get('difficulty', 'Medium').capitalize()} &middot; {m.get('color_count', len(d['legend']))} colours<br>
            {d['grid_w']}&times;{d['grid_h']} grid
        </div>
    </div>
    <div class="body">
        <div class="left-col">
            <div class="grid-area">
                <div class="grid-container">
                    {col_numbers}
                    <div style="position: relative;">
                        {row_numbers}
                        {grid_html}
                        {backstitch_svg}
                    </div>
                </div>
            </div>
            <div class="legend-area">
                {legend_html}
            </div>
        </div>
        <div class="right-col">
            <div>
                <div class="section-title">The Story</div>
                <div class="history-text">{history}</div>
            </div>
            <hr class="divider">
            <div>
                <div class="section-title">Colour Key</div>
                {legend_html}
            </div>
            <hr class="divider">
            {CROSS_STITCH_INSTRUCTIONS}
            <div class="right-footer">
                <div class="footer-brand">&times; XStitchLabs &times;</div>
            </div>
        </div>
    </div>
</div>
</body></html>"""

    Path(output_path).write_text(html)
    print(f"  Option C: {output_path}")


def generate_a4_variants(design_path: str, output_dir: str = None):
    """Generate 3 A4 landscape layout variants."""
    design_path = Path(design_path)
    with open(design_path) as f:
        data = json.load(f)

    d = build_grid_data(data)
    history = get_history(design_path)

    # Cell size for 50/50 A4 landscape: grid panel is ~half of 297mm
    # Page: 297mm wide, 8mm padding each side, 6mm gap = 275mm usable, half = ~137mm
    # Subtract row number margin (~6mm) = ~131mm available for grid
    max_w = 125
    max_h = 180  # 210mm - 14mm padding = ~196mm, leave room for col numbers
    cell_w = max_w / d["grid_w"]
    cell_h = max_h / d["grid_h"]
    cell_mm = min(cell_w, cell_h)
    cell_mm = math.floor(cell_mm * 10) / 10
    cell_mm = min(cell_mm, 4.0)
    cell_mm = max(cell_mm, 1.5)

    out_dir = Path(output_dir) if output_dir else design_path.parent
    stem = design_path.stem

    print(f"Generating A4 landscape for {stem}:")
    print(f"  Grid: {d['grid_w']}x{d['grid_h']}, cell: {cell_mm}mm")

    output_file = out_dir / "pattern_sheet_a4.html"
    generate_option_a(d, cell_mm, history, output_file, design_path=design_path)

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_a4.py <design.json> [output_dir]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    generate_a4_variants(sys.argv[1], out)
