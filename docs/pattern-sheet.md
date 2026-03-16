# Pattern Sheet Generator

Generates branded A5 pattern sheets as HTML files from design JSON files. These are the printable stitching guides included in each kit.

## CLI Usage

Via the `xstitch` CLI (recommended):

```bash
# Generate and open in browser
xstitch pattern-sheet designs/01-three-brothers-riga/design.json

# Specify output path
xstitch pattern-sheet designs/01-three-brothers-riga/design.json -o designs/01-three-brothers-riga/pattern_sheet_a4.html

# Generate without opening browser
xstitch pattern-sheet --no-open designs/01-three-brothers-riga/design.json
```

Or directly via the module:

```bash
python3 -m xstitchlab.export.pattern_sheet.generate <design.json> [output.html]
```

If no output path is given, the HTML is written alongside the input JSON as `<name>_pattern_sheet.html`.

## Printing to PDF

1. Open the generated `.html` file in Chrome
2. Cmd+P (or Ctrl+P)
3. Set paper size to **A5**
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

- `xstitchlab/export/pattern_sheet/template.html` — the HTML/CSS template
- `xstitchlab/export/pattern_sheet/generate.py` — the Python generator
- `xstitchlab/cli.py` — `pattern-sheet` command entry point

## How It Works

The generator reads a design JSON and fills in the HTML template:

1. Calculates cell size to fit the grid within A5 dimensions (auto-scales, capped at 1.5–4mm)
2. Builds an HTML `<table>` with coloured cells and letter symbols
3. Generates an SVG overlay for backstitch segments
4. Builds the legend table
5. Substitutes all placeholders in the template

## Editing the Template

The template is plain HTML/CSS. Edit it directly and re-run the generator to see changes. Template variables use `{{ variable }}` syntax (simple string replacement, not Jinja2).

Available variables: `title`, `cell_size`, `symbol_font_size`, `col_numbers`, `row_numbers`, `grid_html`, `backstitch_svg`, `legend_html`, `stitch_count`, `difficulty`, `color_count`, `grid_width`, `grid_height`.

## Webapp Integration

Not currently integrated — the webapp's "Pattern Sheet" export button still uses the older PIL-based renderer. The HTML-based generator is CLI-only for now. For kit production, use the CLI workflow above.
