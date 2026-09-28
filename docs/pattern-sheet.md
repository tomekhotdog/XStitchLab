# Pattern Sheet Generator

Generates branded pattern sheets as HTML files from a design folder. These are the printable stitching guides included in each kit. Two layouts: **A4 landscape** (chart beside the story, colour key and stitch guide; the one the kits ship with) and **A5 portrait** (chart over legend).

## CLI Usage

```bash
# A4 (default) → designs/01-three-brothers-riga/pattern_sheet_a4.html
xstitch export designs/01-three-brothers-riga --kind sheet

# A5 → designs/01-three-brothers-riga/pattern_sheet_a5.html
xstitch export designs/01-three-brothers-riga --kind sheet --layout a5

# `pattern-sheet` is an alias of `export --kind sheet`
xstitch pattern-sheet designs/01-three-brothers-riga
```

The story paragraph on the A4 sheet comes from `designs/<slug>/history.md` (plain text, one paragraph); the title from `design.json`.

From Python: `xstitchlab.export.pattern_sheet.generate_pattern_sheet(pattern, layout="a4"|"a5", title=..., history=..., output_path=...)`.

## Printing to PDF

1. Open the generated `.html` file in Chrome
2. Cmd+P (or Ctrl+P)
3. Set paper size to **A4** (landscape) or **A5** to match the layout
4. Set margins to **None**
5. Enable **Background graphics**
6. Save as PDF

## What's on the Sheet

- **Branded header** — `× XStitchLabs ×` / `Hanseatic Collection` / tagline, using Cinzel Decorative and Cormorant Garamond fonts
- **Colour symbol grid** — Each stitch cell has a coloured background with a letter symbol overlaid. Major grid lines every 10 stitches, row/column numbers
- **Backstitch overlay** — Black lines rendered as SVG on top of the grid
- **Colour legend** — Table with colour swatch, symbol, DMC code, colour name, stitch count. Background colour marked
- **Footer** — Design title, stitch count, difficulty, colour count, grid dimensions

## Design & Branding

Fonts (Google Fonts, loaded from CDN):
- **Cinzel Decorative Bold** — brand name and collection title
- **Cormorant Garamond** — tagline (italic) and design title (semibold)
- **Barlow** — body text, legend, metadata

Colour palette (matches xstitchlabs.com):
- Coffee `#3E2B1E` — primary text
- Terracotta `#C17B5F` — collection title
- Beige `#D4B896` — rules and dividers
- Stone `#B8AFA4` — secondary text
- Cream `#F5F0E8` — backgrounds

## Files

- `xstitchlab/export/pattern_sheet.py` — the generator (A4 HTML/CSS inline, shared chart/legend builders)
- `xstitchlab/export/pattern_sheet_a5.html` — the A5 HTML/CSS template
- `xstitchlab/cli.py` — `export --kind sheet` / `pattern-sheet` commands
- `designs/<slug>/history.md` — the story text shown on the A4 sheet

## How It Works

The generator takes a `Pattern` (background from `background_index`, outline from `backstitch`):

1. Calculates cell size to fit the grid within the layout's chart area (auto-scales, capped at 1.5–4mm)
2. Builds an HTML `<table>` with coloured cells and letter symbols (background cells blank)
3. Generates an SVG overlay for backstitch segments
4. Builds the legend table
5. Renders the A4 page or substitutes the placeholders in the A5 template

## Editing the A5 Template

The template is plain HTML/CSS. Edit it directly and re-run the generator to see changes. Template variables use `{{ variable }}` syntax (simple string replacement, not Jinja2).

Available variables: `title`, `cell_size`, `symbol_font_size`, `col_numbers`, `row_numbers`, `grid_html`, `backstitch_svg`, `legend_html`, `stitch_count`, `difficulty`, `color_count`, `grid_width`, `grid_height`.

## Webapp Integration

The API's `GET /api/designs/{slug}/export/sheet?layout=a4|a5` runs the same generator (`xstitchlab.library.export_design`, shared with `xstitch export`), writes `pattern_sheet_<layout>.html` into the design folder, and returns it inline, so the editor's export button and the CLI produce identical sheets.
