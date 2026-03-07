"""Generate branded HTML pattern sheets from design JSON files."""

import json
import math
import sys
from pathlib import Path


# PDF-safe symbols (single ASCII/Latin chars that render reliably)
SYMBOLS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "J",
    "K", "L", "M", "N", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z",
    "a", "b", "c", "d", "e", "f", "g", "h", "j",
    "k", "m", "n", "p", "q", "r", "s", "t", "u",
    "v", "w", "x", "y", "z",
    "2", "3", "4", "5", "6", "7", "8", "9",
]


def text_contrast_color(rgb):
    """Return black or white depending on background luminance."""
    r, g, b = rgb
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000" if luminance > 140 else "#fff"


def generate_pattern_sheet(design_path: str, output_path: str = None):
    """Generate an HTML pattern sheet from a design JSON file."""
    design_path = Path(design_path)
    with open(design_path) as f:
        data = json.load(f)

    grid = data["grid"]
    legend = data["legend"]
    metadata = data["metadata"]
    backstitch = data.get("backstitch_segments", [])

    grid_h = len(grid)
    grid_w = len(grid[0]) if grid else 0

    # Find background colour (prefer pure white, then lightest)
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

    # Calculate cell size to fit A5
    # Available space: ~134mm wide, ~150mm tall (after header/legend/footer)
    max_grid_width_mm = 126  # leave room for row numbers
    max_grid_height_mm = 140
    cell_w = max_grid_width_mm / grid_w
    cell_h = max_grid_height_mm / grid_h
    cell_mm = min(cell_w, cell_h)
    cell_mm = math.floor(cell_mm * 10) / 10  # round down to 0.1mm
    cell_mm = min(cell_mm, 4.0)  # cap at 4mm max
    cell_mm = max(cell_mm, 1.5)  # floor at 1.5mm min

    cell_size = f"{cell_mm}mm"
    symbol_font_size = f"{max(3.5, cell_mm * 0.6):.1f}pt"

    # Assign print-friendly symbols
    sym_map = {}
    for i in range(len(legend)):
        sym_map[i] = SYMBOLS[i] if i < len(SYMBOLS) else str(i)

    # Build grid HTML
    rows_html = []
    for y, row in enumerate(grid):
        cells = []
        for x, color_idx in enumerate(row):
            entry = legend[color_idx] if 0 <= color_idx < len(legend) else None
            classes = []
            if x % 10 == 0:
                classes.append("col-major")
            if y % 10 == 0:
                classes.append("row-major")
            cls_attr = f' class="{" ".join(classes)}"' if classes else ""

            if entry and color_idx != bg_idx:
                r, g, b = entry["rgb"]
                fg = text_contrast_color(entry["rgb"])
                sym = sym_map.get(color_idx, "?")
                cells.append(
                    f'<td{cls_attr} style="background:rgb({r},{g},{b});color:{fg}">{sym}</td>'
                )
            else:
                # Background — empty cell
                cells.append(f"<td{cls_attr}></td>")
        rows_html.append(f'<tr>{"".join(cells)}</tr>')

    grid_html = f'<table class="grid-table">{"".join(rows_html)}</table>'

    # Column numbers (every 10)
    # Labels are right-aligned within their cell so the number sits on the grid line
    col_numbers_spans = []
    for x in range(grid_w):
        if x % 10 == 0:
            label = str(x)
        else:
            label = ""
        col_numbers_spans.append(
            f'<span style="width:{cell_size};display:inline-block;text-align:right">{label}</span>'
        )
    col_numbers = (
        f'<div class="grid-numbers-top" style="margin-left:-{cell_size}">'
        f'{"".join(col_numbers_spans)}</div>'
    )

    # Row numbers (every 10)
    # Labels are bottom-aligned within their cell so the number sits on the grid line
    row_numbers_spans = []
    for y in range(grid_h):
        if y % 10 == 0:
            label = str(y)
        else:
            label = ""
        row_numbers_spans.append(
            f'<span style="height:{cell_size};justify-content:flex-end">{label}</span>'
        )
    row_numbers = (
        f'<div class="grid-numbers-left">'
        f'{"".join(row_numbers_spans)}</div>'
    )

    # Backstitch SVG overlay
    if backstitch:
        svg_w = grid_w * cell_mm
        svg_h = grid_h * cell_mm
        lines = []
        for seg in backstitch:
            sx, sy = seg["start"]
            ex, ey = seg["end"]
            x1 = sx * cell_mm
            y1 = sy * cell_mm
            x2 = ex * cell_mm
            y2 = ey * cell_mm
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="#1a1a1a" stroke-width="0.3" stroke-linecap="round"/>'
            )
        backstitch_svg = (
            f'<svg class="backstitch-overlay" '
            f'width="{svg_w}mm" height="{svg_h}mm" '
            f'viewBox="0 0 {svg_w} {svg_h}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'{"".join(lines)}</svg>'
        )
    else:
        backstitch_svg = ""

    # Legend HTML
    legend_rows = []
    for i, entry in enumerate(legend):
        r, g, b = entry["rgb"]
        sym = sym_map.get(i, "?")
        dmc = entry.get("dmc_code", "?")
        name = entry.get("dmc_name", "Unknown")
        count = entry.get("stitch_count", 0)

        if i == bg_idx:
            legend_rows.append(
                f"<tr>"
                f'<td><span class="legend-swatch" style="background:rgb({r},{g},{b})"></span></td>'
                f'<td class="legend-symbol">—</td>'
                f'<td class="legend-dmc">{dmc}</td>'
                f'<td class="legend-name">{name}</td>'
                f'<td class="legend-count legend-bg-note">background</td>'
                f"</tr>"
            )
        else:
            legend_rows.append(
                f"<tr>"
                f'<td><span class="legend-swatch" style="background:rgb({r},{g},{b})"></span></td>'
                f'<td class="legend-symbol">{sym}</td>'
                f'<td class="legend-dmc">{dmc}</td>'
                f'<td class="legend-name">{name}</td>'
                f'<td class="legend-count">{count:,}</td>'
                f"</tr>"
            )

    # Add backstitch row if present
    if backstitch:
        # Expand multi-cell segments to per-cell count
        backstitch_unit_count = 0
        for seg in backstitch:
            sx, sy = seg["start"]
            ex, ey = seg["end"]
            backstitch_unit_count += max(abs(ex - sx), abs(ey - sy))
        legend_rows.append(
            f"<tr>"
            f'<td><span class="legend-swatch" style="background:#1a1a1a"></span></td>'
            f'<td class="legend-symbol">—</td>'
            f'<td class="legend-dmc">310</td>'
            f'<td class="legend-name">Backstitch (1 strand)</td>'
            f'<td class="legend-count">{backstitch_unit_count} segs</td>'
            f"</tr>"
        )

    legend_html = (
        f'<table class="legend-table">'
        f"<thead><tr>"
        f"<th></th><th>Sym</th><th>DMC</th><th>Colour</th><th style='text-align:right'>Stitches</th>"
        f"</tr></thead>"
        f'<tbody>{"".join(legend_rows)}</tbody>'
        f"</table>"
    )

    # Calculate stitch count (excluding background)
    total_stitches = sum(
        entry.get("stitch_count", 0)
        for i, entry in enumerate(legend)
        if i != bg_idx
    )

    # Load template
    template_path = Path(__file__).parent / "template.html"
    template = template_path.read_text()

    # Fill template
    html = template
    replacements = {
        "{{ title }}": metadata.get("title", "Untitled"),
        "{{ cell_size }}": cell_size,
        "{{ symbol_font_size }}": symbol_font_size,
        "{{ col_numbers }}": col_numbers,
        "{{ row_numbers }}": row_numbers,
        "{{ grid_html }}": grid_html,
        "{{ backstitch_svg }}": backstitch_svg,
        "{{ legend_html }}": legend_html,
        "{{ stitch_count }}": f"{total_stitches:,}",
        "{{ difficulty }}": metadata.get("difficulty", "Medium").capitalize(),
        "{{ color_count }}": str(metadata.get("color_count", len(legend))),
        "{{ grid_width }}": str(grid_w),
        "{{ grid_height }}": str(grid_h),
    }
    for key, value in replacements.items():
        html = html.replace(key, str(value))

    # Write output
    if output_path is None:
        stem = design_path.stem.replace("_design", "").replace("_v2", "_v2").replace("_v3", "_v3")
        output_path = design_path.parent / f"{stem}_pattern_sheet.html"
    else:
        output_path = Path(output_path)

    output_path.write_text(html)
    print(f"Generated: {output_path}")
    print(f"  Grid: {grid_w}x{grid_h}, cell size: {cell_mm}mm")
    backstitch_count = sum(max(abs(s["end"][0]-s["start"][0]), abs(s["end"][1]-s["start"][1])) for s in backstitch) if backstitch else 0
    print(f"  {len(legend)} colours, {backstitch_count} backstitch segments")
    print(f"  Open in Chrome → Cmd+P → Save as PDF (A5)")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate.py <design.json> [output.html]")
        sys.exit(1)
    output = sys.argv[2] if len(sys.argv) > 2 else None
    generate_pattern_sheet(sys.argv[1], output)
