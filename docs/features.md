# Features

Terms in bold are defined in `docs/language.md`. Items marked *(new)* are introduced by the 2026-09-26 recipe/editor iteration; everything else exists today and is kept.

## Library

### Browse and open Designs *(new)*

See every **Design** in `designs/`, with thumbnail, title, and whether it has an **Input** and a **Pattern**. Open one into the editor.

**API surface:**
- `GET /api/designs` — list
- `GET /api/designs/{slug}` — open
- `Library` page

### Create a Design *(new)*

Start a new **DesignFolder** from a slug and title.

**API surface:**
- `POST /api/designs`

## Brief

### Write the Brief and attach the Input *(new)*

Write `prompt.md` from the Hanseatic prompt template inside the app, copy it to an external image generator, and drop the generated PNG into the Design as `input.png`.

**API surface:**
- `PUT /api/designs/{slug}/prompt`, `PUT /api/designs/{slug}/input`, `GET /api/designs/{slug}/input.png`
- `xstitch prompt` — CLI template generator
- `BriefPanel` component

## Build

### Run a Recipe with step previews *(new)*

Pick a default **Recipe** (`predesigned` or `photo`) or edit one, then **Run** it on the Input and see a preview for every **Step**.

**API surface:**
- `POST /api/designs/{slug}/run`, `GET /api/recipes/defaults`
- `xstitch run <design_dir>`
- `RecipePanel`, `StepStrip` components

### Tune Operations from their schemas *(new)*

Every **Operation** appears as a card with controls generated from its parameter schema. Add, remove, reorder, and adjust Operations.

**API surface:**
- `GET /api/ops`
- `OpCard`, `ParamField` components

### Pixelate and quantise an image

Reduce an image to a grid of DMC colours: k-means or median-cut quantisation, optional dithering, majority-vote or nearest sampling, LAB or RGB colour matching.

**API surface:**
- Operations `quantize_image`, `resize_image`, `pixelate`

### Clean up a Pattern

Remove isolated stitches, absorb small regions, smooth, straighten edges, fill holes, snap diagonals, connect broken lines, rectangularise, regularise repeated shapes, merge near-identical colours.

**API surface:**
- Operations `remove_isolated`, `absorb_small_regions`, `smooth`, `straighten_edges`, `fill_holes`, `snap_diagonals`, `connect_lines`, `rectangularize`, `regularize_repeats`, `merge_similar_colours`

### Apply the mechanical kit edits *(new)*

Turn the sky into **Fabric**, **Substitute** a DMC code, **Merge** one colour into another, crop or pad the canvas to the kit grid, and convert a drawn outline colour into **Backstitch**.

**API surface:**
- Operations `background_to_fabric`, `substitute_colour`, `merge_colours`, `crop_pad`, `outline_to_backstitch`, `generate_backstitch`
- `POST /api/ops/apply` — apply one Operation to the Pattern open in the editor

## Edit

### Paint and fill stitches

Paint single cells, drag to paint, and *(new)* flood-fill a contiguous region with the selected colour.

**API surface:**
- `Toolbar` tools `paint`, `fill`; store actions `setCells`

### Select, move, and delete regions *(new)*

Drag a rectangle, then move it, delete it to Fabric, or fill it.

**API surface:**
- `Toolbar` tool `select`; store actions `moveSelection`, `clearSelection`, `fillSelection`

### Pick colours and manage the palette

Choose a colour from the **Legend**, *(new)* pick one from the canvas with the eyedropper, and from the palette replace, merge, or set a colour as Fabric.

**API surface:**
- `PalettePanel` component; `POST /api/ops/apply` for replace, merge, fabric

### Draw Backstitch

Toggle unit segments along cell edges, *(new)* drag to draw runs. View in colour, symbol, or backstitch mode.

**API surface:**
- `Toolbar` tool `backstitch`; `LayeredRenderer` backstitch layer

### Undo and redo

Every edit is reversible, including Operations applied from the palette.

**API surface:**
- store `history`

### Navigate the canvas

Zoom with wheel or keys, pan, *(new)* zoom to fit, keyboard cursor painting.

**API surface:**
- `PatternCanvas` component

## Save and Export

### Save the Design *(new: saves to the folder)*

Write `design.json` (with the Recipe) and regenerate `design.md` in the DesignFolder.

**API surface:**
- `PUT /api/designs/{slug}`

### Export previews and PDF

Colour PNG, symbol PNG, realistic thread render, PDF, and JSON, written next to the Design.

**API surface:**
- `GET /api/designs/{slug}/export/{png-color|png-symbol|png-realistic|pdf|json}`
- `xstitch export`

### Generate the Pattern Sheet

Printable A4 or A5 **Pattern Sheet** with symbol chart, legend, stitch diagrams, and history text.

**API surface:**
- `GET /api/designs/{slug}/export/sheet`
- `xstitch export --kind sheet`

### Estimate thread

Per-colour stitch counts, metres, skeins, and 60 cm sections per **Kit**.

**API surface:**
- `GET /api/designs/{slug}/threads`
- `xstitch estimate`

## Quality

### Benchmark Recipes against finished Designs *(new)*

Score each committed Design's Recipe against its final grid and fail the tests when a change regresses it.

**API surface:**
- `tools/benchmark.py`, `xstitch benchmark`, `tests/test_benchmark.py`

## Removed in this iteration

- In-app DALL-E generation (`xstitch generate`) — never used for production designs.
- Upload-and-download editing with an in-memory pattern store.
- The 25-field processing form and "Pre-designed / Photo" mode switch.
