# Research: pipeline, editor, and the gap between generated and handcrafted designs

Date: 2026-09-26. Research phase for the "reproduce the handcrafted designs from the original inputs, expose the tools in the UI" design.

## 1. How the five Hanseatic designs were actually made

Evidence: `designs/0X-*/design.json` embed `pipeline_stages` and `adjustment_stats`; git history; `designs/_shared/hanseatic_style_guide.md`; `docs/pattern-sheet.md`.

1. Hand-written brief in `designs/<slug>/prompt.md`, pasted into Google Gemini (image filenames such as `Gemini_Generated_Image_*` prove this). `xstitchlab/core/ai_generator.py` (DALL-E) is unused scaffolding.
2. Downloaded PNG imported through the web editor in **"Pre-designed" mode** (`backend/app/services/pattern_service.py:169-210`): MiniBatchKMeans at full resolution, majority-vote multi-step resize, `adjust_pattern`. Not `xstitch convert` (CLI photo mode is far further from the finals).
3. Manual edits in the editor and directly in JSON: stray-stitch removal, legend-level colour substitution, colour merge, sky set to fabric, canvas crop/pad/translate (done outside the editor, which has no resize tool), feature removal, window regularisation.
4. Backstitch outline (DMC 310, 1 strand) drawn by hand in the editor; pixel outlines deleted.
5. Pattern sheet via `xstitchlab/export/pattern_sheet/generate.py` (A5, CLI) or the unused-by-CLI `generate_a4.py` (A4, ad hoc scripts). PDF via Chrome print. Packaging in Illustrator/Inkscape.

Legend `stitch_count` values in Tallinn and Gdańsk are stale relative to the grid; `design.md` backstitch counts mix unit and merged segments.

## 2. Gap between pipeline output and final design

Baseline = the `adjusted` stage embedded in each design.json (verified: per-colour counts match `adjustment_stats` exactly). Scripts and renders in the session scratchpad (`step4_compare.py`, `renders/<city>__embedded.png`); to be moved into `tools/` as a benchmark.

| City | Pipeline grid/colours | Final grid/colours | Backstitch merged/unit | Exact match | After nearest-colour | After majority colour map | Dominant manual changes |
|---|---|---|---|---|---|---|---|
| 01 Riga | 45×45 / 8 | 45×45 / 8 | 212 / 589 | 90.6% | 90.6% | 90.6% | Windows squared, gable edges, door |
| 02 Lübeck | 70×38 / 8 | 50×50 / 7 | 216 / 667 | 36.5% | 39.8% | 93.9% | Crop 10 cols each side + pad rows; sky 813→fabric (1,030 cells); legend swap 357→3777 |
| 03 Bergen | 55×55 / 8 | 50×50 / 7 | 267 / 559 | 71.7% | 71.8% | 76.5% | Translate (−7,−8), mountain and ground removed, roof recolour 977→3830, merge 762→3072 |
| 04 Tallinn | 50×50 / 7 | 50×50 / 7 | 207 / 453 | 22.2% | 22.2% | 88.0% | Sky 3761→fabric (1,594 cells); black pixel outline deleted and replaced by backstitch; windows/arcade regularised |
| 05 Gdańsk | 50×50 / 8 | 50×50 / 8 | 170 / 800 | 2.0% | 20.7% | 74.0% | Whole palette reassigned at legend level; fountain and statues removed; windows redrawn; façade simplified |

Manual transformation categories (ordered by cells affected):
1. Background to fabric (sky colour → unstitched).
2. Legend-level colour substitution (change DMC code, grid untouched).
3. Canvas crop / pad / translate to a 50×50 frame.
4. Pixel outline → backstitch layer.
5. Colour merge (tiny-count colour absorbed into neighbour).
6. Feature removal (mountain, fountain, statues, ground strip).
7. Window and roof regularisation (uniform 1×2 / 2×2 blocks, aligned rows).
8. Stray-stitch removal.

Categories 1 to 5 are mechanical and get Lübeck and Tallinn to ~88–94 %. Categories 6 to 8 are judgement edits and need editor tools rather than pipeline ops. Gdańsk is effectively a redesign on top of the pipeline output.

## 3. Core pipeline facts (`xstitchlab/`)

- Pipeline is duplicated: `cli.py:34-99` and `pattern_service.py:63-288` each reimplement resize → quantize → DMC map → Pattern. CLI never runs the adjuster or backstitch; backend bypasses `pixelate()`. `SYMBOLS` is defined three times.
- `Pattern` (`pattern.py:73`) has no backstitch or background field; `from_dict` silently drops `backstitch_segments`. Background detection is triplicated (`pattern.py:130`, `routes/export.py:221`, `pattern_sheet/generate.py:42`).
- `adjuster.py` has 10 cleanup ops, backend only, untested. `backstitch.py` boundary detection, backend only, untested.
- Dead code: `image_input.preprocess_image`, `pixelate_predesigned`, `snap_to_dominant_colors`, `quantize_then_resize`, `two_step_resize`, `ColorMapper.map_image/reduce_to_max_colors/get_substitutes`, `generate_a4.py` (961 lines, three layout variants, reached only by `designs/outputs/designs/generate_hampshire_sheet.py`).
- Bugs: `GET /api/patterns/{id}/threads` raises KeyError (`routes/export.py:225` reads `e["rgb"]` that `ThreadCalculator.estimate_all` never sets). `uv run xstitch` fails with ModuleNotFoundError (broken editable install; `python -m xstitchlab.cli` works).
- Backend stores patterns in a module-level dict (`pattern_service.py:60`), lost on restart. Backend imports core via `sys.path` hacks.
- No backend tests; no adjuster/backstitch tests.

## 4. Frontend facts (`frontend/`)

- `main.js` is 1,175 lines: DOM wiring, thread-cost math, innerHTML templating, API orchestration. Extra module-level state (`selectedFile`, cursor, `dragChanges`) sits outside `PatternState`.
- Undo writes to `patternState.grid` directly, bypassing `setCell` and its events.
- Single canvas, full clear-and-redraw on every zoom/pan/mode/backstitch change. No offscreen cache.
- Tools present: paint cell, palette select, set background (double-click swatch), undo/redo, zoom, view mode (colour/symbol/backstitch), backstitch edge toggle, pipeline-stage viewer (J/K), save, export PNG/PDF/JSON, thread estimate.
- Tools missing that the hand edits required: canvas crop/pad/translate, global colour replace, colour merge, bucket fill, rectangle select/move/delete, eyedropper, zoom-to-fit, live thread count while painting, symbol reassignment, drag-and-drop import.
- UI: three fixed 260px columns, 8 collapsible `<details>` panels of raw form controls with `?` tooltips, native file inputs, dark navy with single red accent, tiny system-font sizes, not responsive.

## 5. Uncommitted work

- `13-salzspeicher-lubeck`: prompt, input, two converter runs, no edits/backstitch/sheet.
- `14-townhall-lubeck`: two prompts and two generated images, not converted.
- `26-town-wall-visby`: prompt only.
- `designs/outputs/designs/3_hampshire_rise_spring*`: one-off gift design in the old flat layout with a bespoke A4 sheet script.
