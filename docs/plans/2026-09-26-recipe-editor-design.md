# Recipe Pipeline and React Editor — Design

Date: 2026-09-26. Status: approved.

## Research

Full research in `docs/plans/2026-09-26-pipeline-recipe-research.md`. Summary:

- The five Hanseatic designs were made by pasting a hand-written brief into Google Gemini, importing the PNG through the editor's "Pre-designed" mode, then hand-editing. The pipeline output is embedded in each design.json, so the gap is measurable.
- Exact match of pipeline output to final: Riga 90.6 %, Lübeck 36.5 %, Bergen 71.7 %, Tallinn 22.2 %, Gdańsk 2.0 %. After the five mechanical edits (background to fabric, legend-level colour substitution, canvas crop/pad/translate, pixel outline to backstitch, colour merge) the ceiling is Lübeck 93.9 %, Tallinn 88.0 %, Riga 90.6 %, Bergen 76.5 %, Gdańsk 74.0 %. The rest is judgement editing: feature removal, window regularisation, stray stitches.
- None of the five mechanical edits exists as a tool. Crop and pad were done outside the editor.
- Core pipeline is duplicated between CLI and backend and they disagree. `Pattern` has no backstitch or background field. About a third of core is dead code. `GET /threads` raises KeyError. `uv run xstitch` entrypoint is broken. Patterns live in an in-memory dict. No backend, adjuster, or backstitch tests.
- Frontend: 1,175-line `main.js`, undo bypasses state, full canvas redraw on every interaction, 25-field settings sidebar, missing fill / select / colour replace / merge / resize canvas / eyedropper / zoom-to-fit.

## Problem Statement

Turning a generated landmark image into a kit-ready cross-stitch pattern takes hours of hand editing, part of it outside the tool, and nothing records what was done. The editor cannot express the edits that were actually needed, the pipeline exists twice, and the backend forgets patterns on restart. New designs (Salzspeicher, Lübeck town hall, Visby wall) are stalled at the import step.

## Solution

A **Recipe** of named **Operations**. Each Operation is a pure function from **Pattern** to **Pattern** (or image to image, or image to Pattern at the boundary) with a typed parameter schema. A Recipe is an ordered list of Operation calls, stored in `design.json`. One registry drives the CLI, the API, the editor sidebar, and a benchmark that scores recipes against the five finished designs. **Design Folders** under `designs/<slug>/` are the library and the storage. The editor is rewritten in React + TypeScript with a layered canvas and the editing tools the hand work needs.

Success bar (agreed): pipeline plus mechanical operations reach about 90 % exact match on Riga, Lübeck, and Tallinn; the remaining edits are done in the editor with the new tools; the benchmark guards regressions. Image generation stays external and is tracked through the Brief step.

## User Stories

1. As the designer, I want to open a design folder from a library view, so that I stop juggling uploads and downloads.
2. As the designer, I want to write the Gemini brief inside the app and drop the generated PNG back in, so that prompt, input, and pattern live together.
3. As the designer, I want to build the pattern from a stack of operations with live previews, so that I can see what each step does and tune it.
4. As the designer, I want "sky to fabric", "swap colour", "merge colours", "crop to 50×50", and "outline to backstitch" as operations, so that the edits I always make take seconds.
5. As the designer, I want fill, rectangle select/move/delete, eyedropper, and backstitch drawing tools, so that the remaining judgement edits happen in the editor.
6. As the designer, I want Save to write design.json and design.md into the folder and exports to land beside them, so that git holds the truth.
7. As the maintainer, I want a benchmark that scores each design's recipe against its committed final, so that pipeline changes cannot silently regress the collection.
8. As a CLI user, I want `xstitch run designs/<slug>` to execute the folder's recipe, so that the CLI and the app behave identically.

## Implementation Decisions

### Core package `xstitchlab/`

**`model/pattern.py`** — `Pattern` dataclass owns: `grid: list[list[int]]` (palette indices), `legend: list[LegendEntry]` (symbol, dmc_code, dmc_name, rgb), `backstitch: list[Segment]` (unit or merged segments, `(x0,y0)-(x1,y1)` in grid-corner coordinates), `background_index: int | None`, `metadata` (title, fabric_count, source: {input: "input.png", prompt: "prompt.md"}), `recipe: list[OpCall]`. Stitch counts, width, height, colour count, difficulty are computed on `to_dict()`, never stored as authoritative. `from_dict()` is lenient: it accepts the legacy keys `backstitch_segments`, `background_color_index`, `pipeline_stages`, `adjustment_stats` (the last two are dropped) so the five committed designs load unchanged. Writing always emits the canonical shape.

**`ops/`** — the registry. Each op is a module exposing:

```python
class Params(BaseModel): ...              # pydantic, doubles as JSON Schema for the UI
NAME = "background_to_fabric"; GROUP = "cleanup"; KIND = "pattern"   # kind: image | pixelate | pattern
TITLE = "Background to fabric"; DESCRIPTION = "..."
def apply(pattern: Pattern, params: Params) -> Pattern
```

`registry.py` discovers ops, exposes `get(name)`, `schemas()`, and `run_recipe(image, recipe) -> RunResult(pattern, steps: list[Step(name, params, pattern)])`. A recipe must be image ops, then exactly one pixelate op, then pattern ops; the registry validates this before running.

Operations in scope:

| Kind | Name | Params | Source |
|---|---|---|---|
| image | `quantize_image` | method (kmeans, median_cut, unique), n_colors, dither | pixelator.quantize_* |
| image | `resize_image` | width, height, method (lanczos, nearest) | pixelator.resize_to_grid |
| pixelate | `pixelate` | width, height, sample (majority, nearest), color_space (lab, rgb) | pixelator.boundary_preserving_resize + ColorMapper |
| pattern | `remove_isolated`, `absorb_small_regions`, `smooth`, `straighten_edges`, `fill_holes`, `snap_diagonals`, `connect_lines`, `rectangularize`, `regularize_repeats` | as in `adjuster.AdjustmentSettings` | adjuster.py, moved |
| pattern | `merge_similar_colours` | threshold | pixelator.merge_similar_colors |
| pattern | `background_to_fabric` | dmc_code or `auto` (largest colour touching the border) | new |
| pattern | `substitute_colour` | from_dmc, to_dmc | new, legend-level |
| pattern | `merge_colours` | from_dmc, to_dmc | new, grid reindex + legend removal |
| pattern | `crop_pad` | width, height, anchor (center, fit_content, offset), offset_x, offset_y | new, pads with background (creates one if absent) |
| pattern | `generate_backstitch` | threshold, min_length, diagonals | backstitch.py, moved |
| pattern | `outline_to_backstitch` | outline_dmc, keep_cells (bool) | new: backstitch on the outline cells' outer boundary, then reassign each outline cell to the majority of its non-outline neighbours |

Default recipes live in `ops/defaults.py`: `predesigned` (quantize_image kmeans → pixelate majority → remove_isolated → absorb_small_regions) and `photo` (resize_image lanczos → quantize_image → pixelate nearest → …). These replace the "Mode" dropdown.

**`library/design_folder.py`** — `DesignFolder(root, slug)` with `list_designs(root)`, `create`, `read_prompt`/`write_prompt`, `read_input`/`write_input`, `read_pattern`/`write_pattern` (atomic write via temp file + rename), `write_design_md` (regenerated from the pattern on every save, matching the current design.md table layout), `export_path(kind)`. The root defaults to `<repo>/designs` and is overridable with `XSTITCH_DESIGNS_DIR`.

**`export/`** — `png.py`, `pdf.py`, `threads.py`, and one `pattern_sheet.py` with `layout: a5 | a4` merging `generate.py` and `generate_a4.py` (option B layout, the one used for the kits). Background detection uses `Pattern.background_index` only.

**Deleted**: `core/ai_generator.py`, `core/image_input.preprocess_image` and thumbnail helpers, `pixelator.pixelate_predesigned/snap_to_dominant_colors/quantize_then_resize/two_step_resize`, `ColorMapper.map_image/reduce_to_max_colors/get_substitutes`, `export/pattern_sheet/generate_a4.py`, `designs/outputs/designs/generate_hampshire_sheet.py` (the Hampshire sheet is regenerated with the merged generator). `prompts/templates.py` stays and backs the Brief step.

**CLI** (`cli.py`): `xstitch run <design_dir> [--recipe predesigned|photo|file.json]`, `xstitch export <design_dir> --kind sheet|pdf|png`, `xstitch estimate`, `xstitch prompt`, `xstitch benchmark`. `convert` becomes an alias for `run` on a bare image. Fix the `uv run xstitch` entrypoint.

### Backend `backend/`

Depends on `xstitchlab` as a workspace package (uv workspace, no `sys.path`). Routes:

| Method | Path | Body / Response |
|---|---|---|
| GET | `/api/designs` | `[{slug, title, has_input, has_pattern, thumbnail_png}]` |
| POST | `/api/designs` | `{slug, title}` → design summary |
| GET | `/api/designs/{slug}` | `{slug, title, prompt, has_input, pattern \| null}` |
| GET | `/api/designs/{slug}/input.png` | the image |
| PUT | `/api/designs/{slug}/input` | multipart PNG |
| PUT | `/api/designs/{slug}/prompt` | `{text}` |
| PUT | `/api/designs/{slug}` | `{pattern}` → saves design.json + design.md |
| POST | `/api/designs/{slug}/run` | `{recipe}` → `{pattern, steps:[{name, params, preview_png, stats}]}` |
| POST | `/api/ops/apply` | `{pattern, op, params}` → `{pattern}` (single pattern op on an in-editor pattern) |
| GET | `/api/ops` | `[{name, group, kind, title, description, schema}]` |
| GET | `/api/recipes/defaults` | `{predesigned: [...], photo: [...]}` |
| GET | `/api/designs/{slug}/export/{kind}` | kind: `png-color`, `png-symbol`, `png-realistic`, `pdf`, `sheet`, `json`; also writes the file into the folder |
| GET | `/api/designs/{slug}/threads` | thread estimates |

The in-memory `_patterns` store and the 25-field upload endpoint are removed.

### Frontend `frontend/` (React 18 + TypeScript + Vite + zustand)

```
src/
  api/          typed client, one function per route
  model/        Pattern types, grid utils (fill, rect move/delete), backstitch normalise/merge, thread maths
  store/        zustand: design, pattern, recipe, runSteps, tool, selection, history (grid + backstitch patches)
  canvas/       PatternCanvas component + LayeredRenderer (cells layer cached offscreen, grid layer, backstitch layer, overlay layer; dirty-rect redraws)
  pages/        Library, Editor
  components/   BriefPanel, RecipePanel (OpCard, ParamField from JSON Schema), Toolbar, PalettePanel, ThreadPanel, ExportMenu, StepStrip
```

Editor tools: paint, fill (contiguous), rectangle select with move/delete/fill, eyedropper, backstitch draw (drag along edges), and palette actions "replace colour", "merge into…", "set as fabric" that call `/api/ops/apply`. Keyboard: number keys for colours, B/G/M/I/L for tools, Ctrl+Z/Y, +/-/0, F for zoom-to-fit. Undo stores patches, and applies them through the store so every subscriber sees them.

Recipe re-run replaces the grid and backstitch; the editor asks for confirmation when unsaved manual edits exist. Manual edits are not merged into a re-run. This is the accepted trade-off against a non-destructive edit log.

Visual direction, to be executed with the frontend-design skill: light "workshop" theme echoing the pattern sheets (Aida cream ground, ink text, terracotta DMC 3830 accent), one display serif for titles and one UI sans, generous 8-pt spacing, native file inputs replaced by drop zones, sidebar cards instead of `<details>` stacks, dark mode via tokens.

### Benchmark `tools/benchmark.py`

For each of the five designs: load `input.png`, run the recipe stored in `design.json`, compare to the committed grid: exact-match %, per-colour confusion, structural vs colour-only cells, backstitch segment count. Prints a table and writes side-by-side PNGs to `tools/benchmark_out/`. `tests/test_benchmark.py` wraps it with thresholds: Riga ≥ 0.90, Lübeck ≥ 0.90, Tallinn ≥ 0.85, Bergen ≥ 0.75, Gdańsk ≥ 0.70 (the last two are documented ceilings, not goals). Each design's recipe is authored during the build by iterating against this score.

### Error handling

- Op parameter validation errors return 422 with op name and field.
- Op runtime failures are wrapped as `OpError(step_index, name, cause)` and returned as 400 with the partial steps so the UI can show which card failed.
- Recipe order violations (pattern op before pixelate) are rejected before any work runs.
- Missing design or input returns 404; save writes atomically so a crash never leaves a half-written design.json.
- The frontend shows errors on the failing card or as a toast, never a silent status line.

## Testing Decisions

- **Ops**: `tests/ops/test_<name>.py` per op on 5×5 or 7×7 grids. Each test states the invariant that matters: `background_to_fabric` changes no other colour's count; `substitute_colour` changes the legend but not the grid; `merge_colours` leaves no index out of range; `crop_pad` preserves every non-background cell under `fit_content`; `outline_to_backstitch` produces closed loops around every removed region.
- **Registry**: kind-order validation, schema export, round-trip of an `OpCall`.
- **Pattern**: lossless round trip including backstitch, background, recipe; lenient load of all five committed designs, parametrised.
- **Library**: read/write on a temp root, atomic write, design.md regeneration.
- **Backend**: FastAPI `TestClient` against a temp `XSTITCH_DESIGNS_DIR` seeded with one committed design; every route.
- **Benchmark**: as above.
- **Frontend**: vitest for `model/` (fill, rect move, segment merge, thread maths), store actions and undo; a Playwright smoke test that opens the library, opens Riga, runs the recipe, paints a cell, saves.
- Existing tests are migrated, not deleted, where the function survives.

## Out of Scope

- In-app image generation (Gemini or any provider); the Brief step only stores prompt and input.
- Pixel-exact replay of manual edits.
- Packaging artwork (Illustrator/Inkscape), the marketing website, kit cost sheets.
- Database storage, multi-user, auth.
- Mobile layout below tablet width.
- Reworking the physical-kit and website plans in `docs/plans/2026-01-24` and `2026-03-03`.
