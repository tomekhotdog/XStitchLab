# Pattern Sheets

Branded A5 pattern sheets for the Hanseatic Collection.

## Files

- `*_pattern_sheet.html` — Individual A5 pattern sheets (HTML, the source of truth)
- `hanseatic_collection_pattern_sheets.pdf` — Combined PDF of all 4 designs

## Regenerating HTML Sheets

```bash
xstitch pattern-sheet designs/outputs/designs/3_brothers_riga_v2.json -o designs/outputs/patternsheets/3_brothers_riga_v2_pattern_sheet.html
xstitch pattern-sheet designs/outputs/designs/bergen_bryggen_v2.json -o designs/outputs/patternsheets/bergen_bryggen_v2_pattern_sheet.html
xstitch pattern-sheet designs/outputs/designs/lubeck_holstentor_v2.json -o designs/outputs/patternsheets/lubeck_holstentor_v2_pattern_sheet.html
xstitch pattern-sheet designs/outputs/designs/tallinn_townhall_design.json -o designs/outputs/patternsheets/tallinn_townhall_pattern_sheet.html
```

## Generating the Combined PDF

Convert each HTML to PDF via Chrome headless, then combine with the macOS `join` tool:

```bash
# Convert each HTML to A5 PDF (5.83 × 8.27 inches)
# --virtual-time-budget=5000 gives Chrome time to load Google Fonts before printing
for name_pair in \
  "riga:3_brothers_riga_v2_pattern_sheet" \
  "bergen:bergen_bryggen_v2_pattern_sheet" \
  "lubeck:lubeck_holstentor_v2_pattern_sheet" \
  "tallinn:tallinn_townhall_pattern_sheet"; do
  name="${name_pair%%:*}"
  file="${name_pair##*:}"
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
    --virtual-time-budget=5000 \
    --print-to-pdf="designs/outputs/patternsheets/${name}.pdf" \
    --print-to-pdf-no-header \
    --paper-width=5.83 --paper-height=8.27 \
    "file://$(pwd)/designs/outputs/patternsheets/${file}.html"
done

# Combine into a single PDF
"/System/Library/Automator/Combine PDF Pages.action/Contents/MacOS/join" -o \
  designs/outputs/patternsheets/hanseatic_collection_pattern_sheets.pdf \
  designs/outputs/patternsheets/riga.pdf \
  designs/outputs/patternsheets/bergen.pdf \
  designs/outputs/patternsheets/lubeck.pdf \
  designs/outputs/patternsheets/tallinn.pdf

# Clean up temp PDFs
rm designs/outputs/patternsheets/{riga,bergen,lubeck,tallinn}.pdf
```

## Printing 2-up on A4

To print two A5 pattern sheets side by side on a single A4 page:

1. Open the combined PDF in Preview
2. Cmd+P
3. Paper size: **A4**
4. Layout → Pages per Sheet: **2**
5. Layout Direction: side-by-side (first icon, left-to-right)
6. Print
