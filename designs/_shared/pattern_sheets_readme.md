# Pattern Sheets

Branded A4 landscape pattern sheets for the Hanseatic Collection.

## Regenerating

Each design's pattern sheet lives inside its own directory. To regenerate:

```bash
# Single design
python3 -m xstitchlab.export.pattern_sheet.generate_a4 designs/01-three-brothers-riga/design.json designs/01-three-brothers-riga/

# All designs
for dir in designs/0*; do
  python3 -m xstitchlab.export.pattern_sheet.generate_a4 "$dir/design.json" "$dir/"
done
```

## Generating a Combined PDF

Convert each HTML to PDF via Chrome headless, then combine:

```bash
for dir in designs/0*; do
  name=$(basename "$dir")
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
    --virtual-time-budget=5000 \
    --print-to-pdf="/tmp/${name}.pdf" \
    --print-to-pdf-no-header \
    --paper-width=11.69 --paper-height=8.27 \
    "file://$(pwd)/${dir}/pattern_sheet_a4.html"
done

# Combine into a single PDF
"/System/Library/Automator/Combine PDF Pages.action/Contents/MacOS/join" -o \
  designs/_shared/hanseatic_collection_pattern_sheets.pdf \
  /tmp/01-three-brothers-riga.pdf \
  /tmp/02-holstentor-lubeck.pdf \
  /tmp/03-bryggen-bergen.pdf \
  /tmp/04-townhall-tallinn.pdf \
  /tmp/05-artus-gdansk.pdf

# Clean up temp PDFs
rm /tmp/0{1,2,3,4,5}-*.pdf
```
