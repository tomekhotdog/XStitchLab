# XStitchLab — Product Spec

XStitchLab turns a generated landmark illustration into a kit-ready cross-stitch pattern: brief → image (external) → **Recipe** of **Operations** → hand editing → exports → physical kit. This spec describes the product after the 2026-09-26 recipe/editor iteration.

## Who it is for

One designer producing the Hanseatic Collection of small (40–50 stitch) architectural kits, plus occasional one-off gift designs.

## Core objects

- **Design Folder** — `designs/<slug>/` holding `prompt.md`, `input.png`, `design.json`, `design.md`, exports, and packaging. The library is the list of these folders. Git is the history.
- **Pattern** — grid of palette indices, legend (DMC code, name, RGB, symbol), backstitch segments, background index (fabric, unstitched), metadata, and the Recipe that produced it. Counts are derived, never stored.
- **Recipe** — ordered list of Operation calls with parameters. Stored in `design.json`. Re-runnable from the CLI, the API, and the editor.
- **Operation** — a pure transformation with a typed parameter schema. Kinds: image → image, image → Pattern (pixelate), Pattern → Pattern.

## Workflow

1. **Brief**: create a design in the library, write the prompt from the Hanseatic template, copy it into Gemini, drop the PNG into the design.
2. **Build**: pick a default Recipe (predesigned or photo), tune operation cards with live step previews, add mechanical operations (background to fabric, substitute colour, merge colours, crop/pad, outline to backstitch).
3. **Edit**: paint, fill, rectangle select/move/delete, eyedropper, backstitch drawing, palette actions (replace, merge, set as fabric). Undo/redo.
4. **Save**: writes `design.json` and regenerates `design.md`.
5. **Export**: colour PNG, symbol PNG, realistic PNG, PDF, A4/A5 pattern sheet, JSON, thread estimates. Files land in the design folder.

## Rules the product enforces

- Style guide defaults: 50×50 grid, 14-count Aida, up to 7 colours plus DMC 310 backstitch outline, background left as fabric.
- A Recipe is validated (image ops, one pixelate, pattern ops) before it runs.
- Re-running a Recipe replaces the grid and asks before discarding unsaved manual edits.
- The benchmark scores every committed design's Recipe against its final grid; thresholds are tests.

## Interfaces

- **Web app**: React editor at :5173 over FastAPI at :8000. Pages: Library, Editor.
- **CLI**: `xstitch run`, `export`, `estimate`, `prompt`, `benchmark`.
- **API**: designs CRUD, `/ops` schemas, `/designs/{slug}/run`, `/ops/apply`, exports, threads.

## Not in the product

In-app image generation, pixel-exact edit replay, packaging artwork, website, database, multi-user, mobile.
