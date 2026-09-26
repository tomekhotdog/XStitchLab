# Ubiquitous Language

Canonical terms for XStitchLab. Use them in code, docs, commits, and conversation. In docs, defined terms are written in bold PascalCase.

| Term | Definition | In code |
|---|---|---|
| **Design** | One landmark kit: brief, input image, pattern, exports, packaging. Identified by a slug such as `02-holstentor-lubeck`. | `Design`, `slug` |
| **DesignFolder** | The directory `designs/<slug>/` that stores a Design. The library is the set of DesignFolders. | `DesignFolder` |
| **Brief** | The hand-written prompt (`prompt.md`) pasted into an external image generator. | `prompt` |
| **Input** | The generated image (`input.png`) a Recipe starts from. | `input` |
| **Pattern** | The stitchable result: grid, legend, backstitch, background, metadata, recipe. | `Pattern` |
| **Grid** | 2-D array of palette indices, one per stitch cell. | `grid` |
| **Legend** | Ordered list of colours in the Pattern: symbol, DMC code, DMC name, RGB. Index into the Legend is the Grid value. | `legend`, `LegendEntry` |
| **Background** | The Legend entry left as bare fabric (not stitched). At most one. | `background_index` |
| **Backstitch** | Outline layer of straight segments between grid corners, DMC 310, one strand. | `backstitch`, `Segment` |
| **Operation** (Op) | A pure, named transformation with a typed parameter schema. Kinds: `image`, `pixelate`, `pattern`. | `ops/<name>.py`, `apply()` |
| **Recipe** | Ordered list of Operation calls with parameters, stored in the Pattern. | `recipe`, `OpCall` |
| **Run** | Executing a Recipe on an Input; yields the Pattern and one Step per Operation. | `run_recipe`, `RunResult` |
| **Step** | The intermediate Pattern (or image) after one Operation in a Run. | `Step` |
| **Pixelate** | The boundary Operation that turns an image into a Pattern by sampling onto the grid and mapping colours to DMC. | `pixelate` |
| **Fabric** | Aida cloth; "to fabric" means make a colour the Background. | `background_to_fabric` |
| **Substitute** | Change a Legend entry's DMC code without touching the Grid. | `substitute_colour` |
| **Merge** | Reassign every cell of one colour to another and drop the source Legend entry. | `merge_colours` |
| **Outline to Backstitch** | Replace a drawn outline colour with Backstitch segments along its boundary. | `outline_to_backstitch` |
| **Benchmark** | Score of a Design's Recipe output against its committed final Grid (exact-match fraction). | `tools/benchmark.py` |
| **Pattern Sheet** | Printable A4 or A5 HTML/PDF with symbol chart, legend, and instructions. | `export/pattern_sheet.py` |
| **Kit** | The physical product: fabric, pre-cut thread, needle, Pattern Sheet, packaging. | — |

Deprecated terms: "Pre-designed mode" and "Photo mode" are now the `predesigned` and `photo` default Recipes. "Adjustments" and "Regularity" panels are cleanup Operations. "Pipeline stages" are Steps.
