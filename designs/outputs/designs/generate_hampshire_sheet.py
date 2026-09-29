"""One-off script: generate A4 pattern sheet for 3 Hampshire Rise Spring."""

import json
import math
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from xstitchlab.export.pattern_sheet.generate_a4 import (
    build_grid_data,
    build_grid_html,
    build_col_numbers,
    build_row_numbers,
    build_backstitch_svg,
    text_contrast_color,
    GOOGLE_FONTS,
    COMMON_CSS,
    STITCH_DIAGRAMS,
)

DESIGN_PATH = Path(__file__).parent / "3_hampshire_rise_spring.json"

HISTORY = (
    "3 Hampshire Rise is a semi-detached residence of distinguished character "
    "in the rolling suburbs of southern England — a property that has, against "
    "all odds and after decades of faithful monthly tribute to the bank, "
    "finally been liberated from the shackles of its mortgage. "
    "Built in the optimistic style of the late 20th century, it features "
    "an attic once shared with a resident squirrel, and a "
    "driveway that has witnessed the full lifecycle of at least four family cars. "
    "The front garden, once home to a tree of considerable stature, now enjoys "
    "unobstructed sunlight — thanks to a legendary act of felling that the "
    "neighbours have not yet forgotten.\n\n"
    "Home to the Szymaniec family of five, the house has stoically endured "
    "school runs, Christmas dinners, and "
    "an ambitious programme of DIY improvements. Rooms have been reorganised, walls have disappeared, shelves "
    "fitted, and every remaining surface painted and repainted until exactly right. "
    "Now mortgage-free, it stands as a monument to patience, persistence, "
    "and the quiet satisfaction of a job well done. "
    "Congratulations are in order — Barclays will miss you terribly."
)

DISPLAY_TITLE = "3 Hampshire Rise"


def build_legend_2col(d):
    """Build a 2-column legend layout (split colours across two mini-tables)."""
    entries = []
    for i, entry in enumerate(d["legend"]):
        if i == d["bg_idx"]:
            continue
        r, g, b = entry["rgb"]
        sym = d["sym_map"].get(i, "?")
        dmc = entry.get("dmc_code", "?")
        name = entry.get("dmc_name", "Unknown")
        count = entry.get("stitch_count", 0)
        entries.append(
            f'<tr><td><span class="legend-swatch" style="background:rgb({r},{g},{b})"></span></td>'
            f'<td class="legend-symbol">{sym}</td><td class="legend-dmc">{dmc}</td>'
            f'<td class="legend-name">{name}</td><td class="legend-count">{count:,}</td></tr>'
        )
    # Add backstitch if present
    if d["backstitch"]:
        entries.append(
            f'<tr><td><span class="legend-swatch" style="background:#1a1a1a"></span></td>'
            f'<td class="legend-symbol">—</td><td class="legend-dmc">310</td>'
            f'<td class="legend-name">Backstitch (1 strand)</td>'
            f'<td class="legend-count">{d["backstitch_unit_count"]} segs</td></tr>'
        )

    mid = (len(entries) + 1) // 2
    col1 = entries[:mid]
    col2 = entries[mid:]

    def make_table(rows):
        return (
            f'<table class="legend-table"><thead><tr>'
            f"<th></th><th>Sym</th><th>DMC</th><th>Colour</th><th style='text-align:right'>Stitches</th>"
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        )

    return (
        f'<div class="legend-2col">'
        f'<div class="legend-col">{make_table(col1)}</div>'
        f'<div class="legend-col">{make_table(col2)}</div>'
        f'</div>'
    )


def generate_sheet(d, cell_mm, history, output_path):
    """Two-column layout: grid left, info right (brand, title, story, 2-col legend, footer)."""
    grid_html, cell_size, symbol_font_size = build_grid_html(d, cell_mm)
    col_numbers = build_col_numbers(d, cell_size)
    row_numbers = build_row_numbers(d, cell_size)
    backstitch_svg = build_backstitch_svg(d, cell_mm)
    legend_html = build_legend_2col(d)
    m = d["metadata"]
    title = DISPLAY_TITLE

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
    /* Left: grid panel */
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
    /* Right: info panel */
    .info-panel {{
        flex: 1; display: flex; flex-direction: column;
        overflow: hidden;
    }}
    .brand-header {{
        text-align: center; padding-bottom: 2.5mm;
        border-bottom: 0.3mm solid var(--beige);
    }}
    .brand {{ font-family: 'Cinzel Decorative', serif; font-size: 11pt; color: var(--coffee); letter-spacing: 0.15em; }}
    .collection {{ font-family: 'Cinzel Decorative', serif; font-size: 7pt; color: var(--terracotta); letter-spacing: 0.12em; text-transform: uppercase; margin-top: 1mm; }}
    .tagline {{ font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 7.5pt; color: var(--stone); margin-top: 0.5mm; }}
    .design-title {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 14pt; color: var(--coffee); text-align: center;
        padding: 2.5mm 0 2mm 0;
    }}
    /* Story */
    .story-section {{
        padding-top: 2mm; border-top: 0.3mm solid var(--beige);
    }}
    .section-title {{
        font-family: 'Cinzel Decorative', serif; font-size: 7pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm;
    }}
    .history-text {{
        font-size: 7.5pt; line-height: 1.5; color: var(--ink);
        text-align: justify;
    }}
    /* Legend */
    .legend-section {{
        padding-top: 2mm; margin-top: 2mm;
        border-top: 0.3mm solid var(--beige);
    }}
    .legend-2col {{
        display: flex; gap: 3mm;
    }}
    .legend-col {{
        flex: 1;
    }}
    .legend-table {{ font-size: 7pt; }}
    .legend-table th {{ font-size: 5.5pt; padding: 0.3mm 0.8mm; }}
    .legend-table td {{ padding: 0.4mm 0.8mm; }}
    .legend-swatch {{ width: 2.8mm; height: 2.8mm; }}
    .legend-symbol {{ font-size: 7pt; }}
    /* Stitch guide */
    .stitch-guide {{
        padding-top: 2mm; margin-top: 2mm;
        border-top: 0.3mm solid var(--beige);
    }}
    .stitch-guide h3 {{
        font-family: 'Cinzel Decorative', serif; font-size: 6.5pt;
        color: var(--terracotta); letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 1.5mm;
    }}
    .diagram-row {{
        display: flex; gap: 3mm;
    }}
    .diagram-item {{
        flex: 1; display: flex; flex-direction: column;
    }}
    .diagram-label {{
        font-family: 'Cormorant Garamond', serif; font-weight: 600;
        font-size: 7pt; color: var(--coffee); margin-bottom: 0.5mm;
    }}
    .diagram-svg {{
        width: 100%; height: auto; display: block; margin-bottom: 0.5mm;
    }}
    .diagram-note {{
        font-size: 5.5pt; color: var(--ink); line-height: 1.3;
    }}
    /* Footer */
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
            <div class="collection">Szymaniec Collection</div>
            <div class="tagline">A cross-stitch tribute to home</div>
        </div>
        <div class="design-title">{title}</div>
        <div class="story-section">
            <div class="section-title">The Story</div>
            <div class="history-text">{history}</div>
        </div>
        <div class="legend-section">
            <div class="section-title">Colour Key</div>
            {legend_html}
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
    print(f"  Generated: {output_path}")


def main():
    with open(DESIGN_PATH) as f:
        data = json.load(f)

    d = build_grid_data(data)

    # Cell size for 50/50 two-column layout
    # Page: 297mm wide, 8mm padding each side, 6mm gap = 275mm, half = ~137mm
    # Subtract row number margin (~6mm) = ~131mm for grid
    max_w = 125
    max_h = 180  # 210mm - 14mm padding
    cell_w = max_w / d["grid_w"]
    cell_h = max_h / d["grid_h"]
    cell_mm = min(cell_w, cell_h)
    cell_mm = math.floor(cell_mm * 10) / 10
    cell_mm = min(cell_mm, 4.0)
    cell_mm = max(cell_mm, 1.5)

    d["metadata"]["title"] = DISPLAY_TITLE

    output_file = DESIGN_PATH.parent / "3_hampshire_rise_spring_pattern_sheet_a4.html"

    print(f"Generating A4 pattern sheet for {DISPLAY_TITLE}:")
    print(f"  Grid: {d['grid_w']}x{d['grid_h']}, cell: {cell_mm}mm")

    generate_sheet(d, cell_mm, HISTORY, output_file)

    print("Done.")
    print(f"\nOpen in Chrome → Cmd+P → A4 Landscape → No margins → Background graphics → Save as PDF")


if __name__ == "__main__":
    main()
