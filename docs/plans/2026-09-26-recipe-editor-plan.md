# Recipe Pipeline and React Editor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use tomek-superpowers:build to implement this plan task-by-task.

**Goal:** Replace the duplicated image pipeline with a registry of typed Operations run as Recipes stored in design folders, and rewrite the editor in React with the tools the handcrafted designs needed, verified by a benchmark against the five finished designs.

**Architecture:** `xstitchlab/` (pure Python: Pattern model, `ops/` registry, `library/` design folders, `export/`) ← `backend/` (thin FastAPI over the library and registry) ← `frontend/` (React + TypeScript + Vite + zustand, layered canvas). `tools/benchmark.py` scores recipes against committed designs and runs under pytest.

**Tech Stack:** Python 3.11, pydantic 2, numpy, scikit-learn, scipy, Pillow, FastAPI, typer; React 18, TypeScript, Vite, zustand, vitest, Playwright.

**Design:** `docs/plans/2026-09-26-recipe-editor-design.md`. Terms: `docs/language.md`.

**Baseline before work:** `uv run pytest tests/ -q` → 63 passed, 2 failed (`test_integration.py::TestFullPipeline::test_end_to_end_pipeline`, `test_thread_calc.py::TestQuickEstimate::test_quick_estimate`). Both pre-date this work; Task 7 fixes or migrates them. `uv run xstitch` is broken (ModuleNotFoundError); use `uv run python -m xstitchlab.cli` until Task 1 fixes it.

**Conventions for every task**

- Branch: `recipe-editor` (already created). Commit after each task with a message body ending in `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Python: `uv run pytest <path> -q`. Frontend: `npm test` (vitest) inside `frontend/`.
- Do not commit the user's unrelated untracked files (`CLAUDE.md`, `designs/13-*`, `designs/14-*`, `designs/26-*`, `docs/design_ideas.md`, `docs/guides/`, `docs/kit_costs.md`, `designs/outputs/**`). Stage files by name.
- Deviation from the design doc, decided here: the Pattern model stays in `xstitchlab/core/pattern.py` (no new `model/` package) to keep existing imports working. `DMCColor` and `DMCPalette` are untouched.
- Backstitch coordinates are grid-corner coordinates: a segment `{start:[x1,y1], end:[x2,y2]}` runs between corners, so a horizontal edge on top of cell (x, y) is `[x,y]→[x+1,y]`. Merged segments may span several cells; unit segments span one.
- Legend index = grid value. `background_index` names the legend entry left as fabric.

---

### Task 1: Pattern model owns backstitch, background, and recipe; fix the CLI entrypoint ✅ DONE (72d859a, 14e3272, +cli fix)
**Depends on:** none

> Outcome: 75 tests pass. The `xstitch` console script failure is environmental (a file-sync tool re-hides `.venv` `.pth` files); the package install is correct. Ops in later tasks must build new `Pattern` objects (or call `count_stitches()`) after mutating grids, because `metadata` counts are cached until then.

**Files:**
- Modify: `xstitchlab/core/pattern.py`
- Modify: `pyproject.toml` (remove `openai` dependency; keep `[project.scripts]`), then run `uv sync --reinstall-package xstitchlab` so `uv run xstitch --help` works
- Test: `tests/test_pattern_model.py` (new; keep the existing `tests/test_pattern.py`)

**Step 1: Write the failing tests**

```python
# tests/test_pattern_model.py
import json
from pathlib import Path
import pytest
from xstitchlab.core.pattern import Pattern, DMCColor, ColorLegendEntry, PatternMetadata, Segment, OpCall

DESIGNS = sorted(p for p in Path("designs").glob("0*/design.json"))

def make_pattern():
    legend = [
        ColorLegendEntry(DMCColor("3865", "Winter White", (249, 247, 241)), "●"),
        ColorLegendEntry(DMCColor("310", "Black", (0, 0, 0)), "■"),
    ]
    grid = [[0, 0, 1], [0, 1, 1], [1, 1, 1]]
    return Pattern(grid=grid, legend=legend, metadata=PatternMetadata(title="t"),
                   backstitch=[Segment(0, 1, 2, 1)], background_index=0,
                   recipe=[OpCall("pixelate", {"width": 3, "height": 3})])

def test_round_trip_is_lossless():
    p = make_pattern()
    d = p.to_dict()
    q = Pattern.from_dict(d)
    assert q.grid == p.grid
    assert [e.dmc_color.code for e in q.legend] == ["3865", "310"]
    assert q.backstitch == [Segment(0, 1, 2, 1)]
    assert q.background_index == 0
    assert q.recipe == [OpCall("pixelate", {"width": 3, "height": 3})]
    assert q.to_dict() == d

def test_to_dict_derives_counts_and_excludes_background():
    d = make_pattern().to_dict()
    assert d["metadata"]["width"] == 3 and d["metadata"]["height"] == 3
    assert d["legend"][0]["stitch_count"] == 3
    assert d["legend"][1]["stitch_count"] == 6
    assert d["metadata"]["total_stitches"] == 6          # background excluded
    assert d["metadata"]["color_count"] == 2
    assert d["background_index"] == 0
    assert d["backstitch"] == [{"start": [0, 1], "end": [2, 1]}]
    assert d["recipe"] == [{"op": "pixelate", "params": {"width": 3, "height": 3}}]
    assert "backstitch_segments" not in d and "pipeline_stages" not in d

def test_stale_stitch_counts_in_input_are_ignored():
    d = make_pattern().to_dict()
    d["legend"][1]["stitch_count"] = 999
    assert Pattern.from_dict(d).to_dict()["legend"][1]["stitch_count"] == 6

@pytest.mark.parametrize("path", DESIGNS, ids=[p.parent.name for p in DESIGNS])
def test_legacy_designs_load_and_keep_totals(path):
    raw = json.loads(path.read_text())
    p = Pattern.from_dict(raw)
    d = p.to_dict()
    assert len(p.backstitch) == len(raw["backstitch_segments"])
    assert p.background_index is not None
    if "background_color_index" in raw:
        assert p.background_index == raw["background_color_index"]
    assert d["metadata"]["total_stitches"] == raw["metadata"]["total_stitches"]
    assert d["metadata"]["width"] == raw["metadata"]["width"]

def test_segment_from_legacy_and_short_forms():
    assert Segment.from_dict({"start": [1, 2], "end": [3, 2]}) == Segment(1, 2, 3, 2)
    assert Segment.from_dict({"x1": 1, "y1": 2, "x2": 3, "y2": 2}) == Segment(1, 2, 3, 2)
```

Note for the legacy totals assertion: Riga's committed `total_stitches` is 1203 in metadata while design.md says 1182; the test compares to `raw["metadata"]["total_stitches"]` only if the heuristic background is the same entry the old code picked. If a design fails this assertion, print both numbers and check whether the difference equals one legend entry's count; if the old heuristic (pure white, else brightest) picks a different entry than the committed metadata implies, keep the heuristic and relax the assertion to `abs(diff) == 0 or the entry count` with a comment naming the design. Do not special-case by slug.

**Step 2: Run to verify failure**
Run: `uv run pytest tests/test_pattern_model.py -q` → ImportError on `Segment`/`OpCall` (FAIL).

**Step 3: Implement**

In `xstitchlab/core/pattern.py` add, after `PatternMetadata`:

```python
@dataclass(frozen=True)
class Segment:
    """Backstitch segment between grid corners (x, y in 0..width / 0..height)."""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def is_unit(self) -> bool:
        return max(abs(self.x2 - self.x1), abs(self.y2 - self.y1)) == 1

    def to_dict(self) -> dict:
        return {"start": [self.x1, self.y1], "end": [self.x2, self.y2]}

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        if "start" in d:
            (x1, y1), (x2, y2) = d["start"], d["end"]
            return cls(int(x1), int(y1), int(x2), int(y2))
        return cls(int(d["x1"]), int(d["y1"]), int(d["x2"]), int(d["y2"]))


@dataclass
class OpCall:
    op: str
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"op": self.op, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: dict) -> "OpCall":
        return cls(op=d["op"], params=dict(d.get("params", {})))
```

Change `Pattern`:

```python
@dataclass
class Pattern:
    grid: list[list[int]]
    legend: list[ColorLegendEntry] = field(default_factory=list)
    metadata: PatternMetadata = field(default_factory=PatternMetadata)
    backstitch: list[Segment] = field(default_factory=list)
    background_index: Optional[int] = None
    recipe: list[OpCall] = field(default_factory=list)
    SYMBOLS: list[str] = field(default_factory=lambda: [...unchanged...])

    def __post_init__(self):
        self.count_stitches()

    @property
    def width(self) -> int: return len(self.grid[0]) if self.grid else 0
    @property
    def height(self) -> int: return len(self.grid)

    def guess_background_index(self) -> Optional[int]:
        """Legacy heuristic: pure white, else brightest legend entry."""
        for idx, e in enumerate(self.legend):
            if tuple(e.dmc_color.rgb) == (255, 255, 255):
                return idx
        best, best_b = None, -1.0
        for idx, e in enumerate(self.legend):
            r, g, b = e.dmc_color.rgb
            bright = 0.299 * r + 0.587 * g + 0.114 * b
            if bright > best_b:
                best, best_b = idx, bright
        return best

    def count_stitches(self) -> dict[str, int]:
        counts: dict[int, int] = {}
        for row in self.grid:
            for v in row:
                counts[v] = counts.get(v, 0) + 1
        for idx, e in enumerate(self.legend):
            e.stitch_count = counts.get(idx, 0)
        bg = self.background_index
        self.metadata.width, self.metadata.height = self.width, self.height
        self.metadata.color_count = len(self.legend)
        self.metadata.total_stitches = sum(e.stitch_count for i, e in enumerate(self.legend) if i != bg)
        self.metadata.difficulty = self.metadata.get_difficulty_rating()
        return {self.legend[i].dmc_color.code: c for i, c in counts.items() if i < len(self.legend)}

    def copy(self) -> "Pattern":
        import copy as _copy
        return _copy.deepcopy(self)

    def to_dict(self) -> dict:
        self.count_stitches()
        return {
            "metadata": {
                "title": self.metadata.title, "width": self.width, "height": self.height,
                "color_count": self.metadata.color_count, "total_stitches": self.metadata.total_stitches,
                "difficulty": self.metadata.difficulty, "fabric_count": self.metadata.fabric_count,
                "fabric_width_inches": round(self.metadata.fabric_width_inches, 1),
                "fabric_height_inches": round(self.metadata.fabric_height_inches, 1),
                "source_image": self.metadata.source_image,
            },
            "legend": [
                {"symbol": e.symbol, "dmc_code": e.dmc_color.code, "dmc_name": e.dmc_color.name,
                 "rgb": list(e.dmc_color.rgb), "stitch_count": e.stitch_count}
                for e in self.legend
            ],
            "grid": [list(row) for row in self.grid],
            "backstitch": [s.to_dict() for s in self.backstitch],
            "background_index": self.background_index,
            "recipe": [c.to_dict() for c in self.recipe],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        legend = [
            ColorLegendEntry(DMCColor(code=str(e["dmc_code"]), name=e.get("dmc_name", ""), rgb=tuple(e["rgb"])),
                             symbol=e.get("symbol", "?"))
            for e in data.get("legend", [])
        ]
        m = data.get("metadata", {})
        metadata = PatternMetadata(title=m.get("title", "Untitled Pattern"),
                                   fabric_count=int(m.get("fabric_count", 14)),
                                   source_image=m.get("source_image"))
        raw_bs = data.get("backstitch", data.get("backstitch_segments", []))
        backstitch = [Segment.from_dict(s) for s in raw_bs]
        bg = data.get("background_index", data.get("background_color_index"))
        recipe = [OpCall.from_dict(c) for c in data.get("recipe", [])]
        p = cls(grid=[list(r) for r in data["grid"]], legend=legend, metadata=metadata,
                backstitch=backstitch, background_index=bg, recipe=recipe)
        if p.background_index is None:
            p.background_index = p.guess_background_index()
            p.count_stitches()
        return p
```

Keep `save`/`load`, `get_symbol`, `get_color_at`, `DMCPalette` as they are. Search the repo for callers of `metadata.width` assignments or `pattern.metadata.total_stitches` and confirm nothing writes them directly (grep `metadata.width =`); `pattern_service.py` may — leave it, it is deleted in Task 9.

Fix entrypoint: in `pyproject.toml` remove `"openai>=1.0.0"` (Task 7 deletes the generator; the import in `cli.py` is lazy, verify with `grep -n openai xstitchlab/cli.py` and make it lazy if not). Run `uv sync --reinstall-package xstitchlab` and confirm `uv run xstitch --help` prints the command list.

**Step 4: Run tests**
`uv run pytest tests/test_pattern_model.py tests/test_pattern.py -q` → all pass. `uv run pytest tests/ -q` → same 2 pre-existing failures only.

**Step 5: Commit**
`git add xstitchlab/core/pattern.py pyproject.toml uv.lock tests/test_pattern_model.py && git commit -m "Pattern owns backstitch, background, and recipe; fix xstitch entrypoint"`

---

### Task 2: Operation protocol, registry, and `run_recipe` ✅ DONE (6e704fc + review fixes)
**Depends on:** Task 1

> Outcome: 101 tests pass. Every op's `Params` must subclass `xstitchlab.ops.base.OpParams` (extra keys forbidden). `register()` validates `KIND`. The `noop` op has `GROUP="test"`; the backend must filter that group out of `/api/ops`.

**Files:**
- Create: `xstitchlab/ops/__init__.py`, `xstitchlab/ops/base.py`, `xstitchlab/ops/registry.py`, `xstitchlab/ops/noop.py` (a pattern op used only by tests: `NAME="noop"`)
- Test: `tests/ops/__init__.py`, `tests/ops/test_registry.py`

**Step 1: Failing tests**

```python
# tests/ops/test_registry.py
import pytest
from PIL import Image
from pydantic import ValidationError
from xstitchlab.ops import registry
from xstitchlab.ops.base import OpError
from xstitchlab.core.pattern import OpCall

def test_registry_lists_ops_with_schema():
    ops = registry.schemas()
    names = {o["name"] for o in ops}
    assert "noop" in names
    noop = next(o for o in ops if o["name"] == "noop")
    assert noop["kind"] == "pattern" and noop["group"] and noop["title"]
    assert noop["schema"]["type"] == "object"

def test_validate_recipe_requires_one_pixelate_after_image_ops():
    with pytest.raises(OpError, match="pixelate"):
        registry.validate_recipe([OpCall("noop")])            # pattern op with no pixelate
    with pytest.raises(OpError, match="unknown"):
        registry.validate_recipe([OpCall("does_not_exist")])

def test_validate_params_uses_pydantic():
    with pytest.raises(ValidationError):
        registry.get("noop").Params(times="three")

def test_run_recipe_on_pattern_skips_image_stage():
    from tests.ops.helpers import small_pattern
    p = small_pattern()
    result = registry.run_pattern_ops(p, [OpCall("noop", {"times": 2})])
    assert result.pattern.grid == p.grid
    assert [s.name for s in result.steps] == ["noop"]
    assert result.pattern.recipe == [OpCall("noop", {"times": 2})]
```

Create `tests/ops/helpers.py` with `small_pattern()` returning a 5×5 Pattern with three legend entries (`3865` white index 0 as background, `310` black index 1, `3830` terracotta index 2) and grid:

```
0 0 0 0 0
0 1 1 1 0
0 1 2 1 0
0 1 1 1 0
0 0 0 0 0
```

**Step 2: Run** `uv run pytest tests/ops -q` → ImportError (FAIL).

**Step 3: Implement**

`xstitchlab/ops/base.py`:

```python
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable
from PIL import Image
from pydantic import BaseModel
from xstitchlab.core.pattern import Pattern, OpCall

Kind = Literal["image", "pixelate", "pattern"]

class OpError(Exception):
    def __init__(self, message: str, step_index: int | None = None, op: str | None = None):
        super().__init__(message); self.step_index = step_index; self.op = op

@runtime_checkable
class Operation(Protocol):
    NAME: str
    KIND: Kind
    GROUP: str          # "import" | "cleanup" | "kit" | "outline"
    TITLE: str
    DESCRIPTION: str
    Params: type[BaseModel]
    @staticmethod
    def apply(subject, params): ...   # image->image, image->Pattern, or Pattern->Pattern by KIND

@dataclass
class Step:
    name: str
    params: dict
    result: "Image.Image | Pattern"
    stats: dict = field(default_factory=dict)

@dataclass
class RunResult:
    pattern: Pattern
    steps: list[Step]
```

`xstitchlab/ops/registry.py`: imports every module in `xstitchlab.ops` except `base`/`registry` via `pkgutil.iter_modules`, keeps `dict[str, module]`. Functions:

- `get(name)` → module or `OpError("unknown op: name")`.
- `schemas()` → list of `{name, kind, group, title, description, schema: module.Params.model_json_schema()}` sorted by group then name.
- `validate_recipe(recipe: list[OpCall])` → checks names exist, validates params via `Params(**params)`, enforces order: zero or more `image`, exactly one `pixelate`, zero or more `pattern`. Raises `OpError` with `step_index`.
- `run_recipe(image: Image.Image, recipe) -> RunResult`: validate, then fold; after the pixelate op the subject is a `Pattern`. Each pattern op receives `pattern.copy()`. Wrap exceptions in `OpError(f"{name} failed: {e}", i, name)`. Set `result.pattern.recipe = recipe` at the end. Stats per step: for pattern results `{"width","height","colors","stitches","backstitch"}`; for images `{"width","height"}`.
- `run_pattern_ops(pattern, ops: list[OpCall]) -> RunResult`: same fold starting from a Pattern, only pattern ops allowed, `pattern.recipe` extended with `ops`.
- `apply_one(pattern, call: OpCall) -> Pattern` convenience for the API.

`xstitchlab/ops/noop.py`: `Params(times: int = 1)`, `apply` returns the pattern unchanged.

**Step 4:** `uv run pytest tests/ops -q` → pass. **Step 5:** commit `feat(ops): operation protocol, registry, run_recipe`.

---

### Task 3: Import operations and default recipes, `xstitch run`, and the benchmark table ✅ DONE (878cb16 + review fixes)
**Depends on:** Task 2

> Outcome: 129 tests pass. PREDESIGNED default uses `steps: 1` (Riga scores 0.906 with it; 0.586 with 3 steps because `boundary_preserving_resize` pads intermediates up to whole blocks — a core padding bug left for a follow-up). `benchmark_design` returns `size_ok`, not `width_ok`. Task 4 must append its cleanup ops to PREDESIGNED with `steps` unchanged.

**Files:**
- Create: `xstitchlab/ops/quantize_image.py`, `xstitchlab/ops/resize_image.py`, `xstitchlab/ops/pixelate.py`, `xstitchlab/ops/defaults.py`
- Create: `tools/__init__.py`, `tools/benchmark.py`
- Modify: `xstitchlab/cli.py` (add `run`, `benchmark`; make `convert` call `run_recipe` with the `photo` default)
- Test: `tests/ops/test_import_ops.py`, `tests/test_benchmark_tool.py`

**Ops**

- `quantize_image` (KIND image, GROUP import): `Params(method: Literal["kmeans","median_cut","unique"]="kmeans", n_colors: int = Field(8, ge=2, le=64), dither: bool=False)`. kmeans uses `sklearn.cluster.MiniBatchKMeans(n_clusters, random_state=42, n_init=1, batch_size=1024)` on the RGB pixels (this reproduces the backend's predesigned path); `median_cut` calls `pixelator.quantize_colors_median_cut`; `unique` calls `pixelator.extract_unique_colors` and raises `OpError` if more than 256 colours; `dither=True` calls `pixelator.apply_dithering`. Returns an RGB image with at most `n_colors` colours.
- `resize_image` (image, import): `Params(width: int = Field(50, ge=4, le=400), height: int | None = None, method: Literal["lanczos","nearest"]="lanczos")`. Calls `pixelator.resize_to_grid`.
- `pixelate` (pixelate, import): `Params(width: int = 50, height: int | None = None, sample: Literal["majority","nearest"]="majority", steps: int = Field(3, ge=1, le=6), color_space: Literal["lab","rgb"]="lab", fabric_count: int = 14)`. If the image is already ≤ target size, no resize. `majority` → `pixelator.multi_step_resize(img, width, num_steps=steps, mode="majority")` when steps>1 else `boundary_preserving_resize`; `nearest` → `resize_to_grid(..., method="nearest")`. Then palette = unique colours of the resized image (`extract_unique_colors`), indices via `get_color_indices`, DMC mapping via `ColorMapper(use_lab=color_space=="lab").map_palette(palette)`. If two palette colours map to the same DMC code, merge their indices (keep the first). Build `Pattern(grid, legend with symbols from Pattern.SYMBOLS, metadata(title=""), background_index=None)`; then set `background_index = pattern.guess_background_index()`. Note `height` defaults to preserving aspect ratio.

`defaults.py`:

```python
PREDESIGNED = [OpCall("quantize_image", {"method": "kmeans", "n_colors": 8}),
               OpCall("pixelate", {"width": 50, "sample": "majority", "steps": 3}),
               OpCall("remove_isolated", {}), OpCall("fill_holes", {}), OpCall("snap_diagonals", {}),
               OpCall("connect_lines", {}), OpCall("rectangularize", {})]
PHOTO = [OpCall("resize_image", {"width": 50, "method": "lanczos"}),
         OpCall("quantize_image", {"method": "kmeans", "n_colors": 8}),
         OpCall("pixelate", {"width": 50, "sample": "nearest"})]
DEFAULTS = {"predesigned": PREDESIGNED, "photo": PHOTO}
```

The cleanup ops referenced here are created in Task 4; until then `PREDESIGNED` in this task contains only the first two calls, and Task 4 appends the rest.

**CLI**: `xstitch run <design_dir_or_image> [--recipe predesigned|photo|<file.json>] [--out design.json] [--width 50] [--colors 8]`. For a directory, reads `input.png` and, if `design.json` exists and has a non-empty recipe and `--recipe` is not given, uses it; writes the result to `--out` (default: `<dir>/run.json`, never overwriting `design.json` unless `--out` says so). Prints a Rich table of steps with stats. `--width/--colors` override the matching params in the chosen default. `convert` keeps its flags and delegates to `run` with the `photo` recipe.

**Benchmark** `tools/benchmark.py`:

```python
def score(candidate: Pattern, final: Pattern) -> dict:
    """exact: fraction of cells whose DMC code matches (grids must be same size; else 0 with 'size_mismatch')."""
def benchmark_design(design_dir: Path, recipe: list[OpCall] | None = None) -> dict:
    # loads input.png + design.json, runs recipe (design's own if None), returns
    # {slug, exact, width_ok, colors_final, colors_candidate, backstitch_final, backstitch_candidate, confusion: {(cand_dmc, final_dmc): count}}
def main(design_dirs, out_dir="tools/benchmark_out", render=True) -> list[dict]: prints a table and writes side-by-side PNGs (input | candidate | final | diff) using visualizer.render_color_preview at 8 px per cell.
```

Diff rendering: red cell where DMC differs. `xstitch benchmark [dirs...]` calls `main`.

**Tests**

- `test_import_ops.py`: quantize a 40×40 image with 4 flat colour blocks (from `conftest.sample_rgb_image`) → ≤4 colours; pixelate a 100×100 four-block image to 10×10 majority → grid has exactly 4 DMC codes and each quadrant is uniform; pixelate merges duplicate DMC mappings (two near-identical greys → one legend entry); default recipes validate (`registry.validate_recipe(DEFAULTS[k])` for each key).
- `test_benchmark_tool.py`: `score` of a pattern against itself is 1.0; against a copy with one cell changed on a 5×5 grid is 0.96; size mismatch returns 0 with a flag.

**Verify end to end**: `uv run xstitch run designs/01-three-brothers-riga --recipe predesigned --width 45 --out /tmp/riga_run.json` prints a step table; `uv run xstitch benchmark designs/01-three-brothers-riga` prints a row with an `exact` score (expect roughly 0.5–0.9; the number is recorded, not asserted, until Task 6).

Commit: `feat(ops): import operations, default recipes, xstitch run, benchmark tool`.

---

### Task 4: Cleanup operations migrated from the adjuster, plus `merge_similar_colours` and `generate_backstitch` ✅ DONE (1daf452 + review fixes)
**Depends on:** Task 2 (parallel with Task 3)

> Outcome: 177 tests pass. Riga with the full PREDESIGNED default scores 0.889 (the five cleanup ops cost ~1.7 points; Task 6 tunes per design). `_segments.merge_collinear` is safe on any backstitch (non-axis segments pass through). Cleanup ops keep zero-count legend entries; `_grid.drop_unused_colours` exists for Task 5/6 to use. Decision: one small file per op stays (mirrors one UI card; consistent with import ops) rather than a table-driven registration.

**Files:**
- Create: one module per op in `xstitchlab/ops/`: `remove_isolated.py`, `absorb_small_regions.py` (`min_region_size: int = Field(2, ge=2)`), `smooth.py` (`iterations: int = Field(1, ge=1, le=5)`), `straighten_edges.py`, `fill_holes.py`, `snap_diagonals.py`, `connect_lines.py`, `rectangularize.py`, `regularize_repeats.py` (`min_group_size: int = 3`, `enforce_repetition: bool = False`, `similarity: float = 0.8`), `merge_similar_colours.py` (`threshold: int = Field(20, ge=1, le=100)`), `generate_backstitch.py` (`min_contrast: int = 50`, `diagonals: bool = False`, `replace: bool = True` — when True the pattern's backstitch is replaced, else appended).
- Create: `xstitchlab/ops/_grid.py` with helpers `to_indices(pattern) -> np.ndarray`, `to_palette(pattern) -> np.ndarray (n,3)`, `from_indices(pattern, indices, palette=None) -> Pattern` (rebuilds grid; when `palette` is given with fewer rows, remaps legend by matching RGB and drops unused entries, preserving `background_index` by RGB), `drop_unused_colours(pattern) -> Pattern` (removes legend entries with zero cells, reindexes grid, keeps background if it still exists, else sets background_index None).
- Keep `xstitchlab/core/adjuster.py` functions as the implementation (import them); delete `AdjustmentSettings`, `adjust_pattern`, and `indices_to_image` after Task 9 removes their last caller. Same for `backstitch.generate_backstitch`: the op calls `detect_boundaries` + `merge_segments` and converts `BackstitchSegment` → `Segment`.
- Test: `tests/ops/test_cleanup_ops.py`, `tests/ops/test_backstitch_op.py`, `tests/ops/test_grid_helpers.py`

**Tests (each names the invariant it protects)**

- `remove_isolated`: a single stray index in a 7×7 field of another colour is absorbed; a 2×2 block is not.
- `fill_holes`: a 1-cell hole inside a 5×5 block is filled; the border is unchanged.
- `absorb_small_regions(min_region_size=3)`: a 2-cell region disappears, a 3-cell region stays.
- `smooth`, `straighten_edges`, `snap_diagonals`, `connect_lines`, `rectangularize`, `regularize_repeats`: for each, a smoke test that the op returns a Pattern of the same size with all grid values inside the legend, plus one behavioural case for `rectangularize` (an L-shaped blob of 6 cells becomes its bounding rectangle or stays, whichever the current adjuster does; assert on the current behaviour after observing it once and comment why).
- `merge_similar_colours(threshold=30)`: two legend entries with RGB distance 10 become one and the grid has no out-of-range index; `background_index` follows the surviving entry.
- `drop_unused_colours`: unused entry removed, indices remapped, background preserved by RGB.
- `generate_backstitch`: on `small_pattern()`, segments form the closed ring around the 3×3 block (12 unit edges before merge, 4 merged segments); `replace=False` appends to existing.

Commit: `feat(ops): cleanup and backstitch operations`.

---

### Task 5: Mechanical kit operations ✅ DONE (ade4859 + review fixes)
**Depends on:** Task 4

> Outcome: 212 tests pass. Benchmark now counts fabric-vs-fabric as a match (finals name fabric `White`/`B5200`). Untuned probes: Tallinn 0.900 (predesigned w=50 + background_to_fabric auto + outline_to_backstitch auto), Lübeck 0.924 (predesigned w=70 + background_to_fabric auto + crop_pad 50×50 fit_content). Helpers: `_legend.py`, `_grid.keep_entries`.

**Files:**
- Create: `xstitchlab/ops/background_to_fabric.py`, `substitute_colour.py`, `merge_colours.py`, `crop_pad.py`, `outline_to_backstitch.py`
- Test: `tests/ops/test_kit_ops.py`

**Specs**

- `background_to_fabric` (GROUP kit): `Params(dmc_code: str = "auto")`. `auto` = the legend entry with the most cells on the outer border ring. Sets `background_index` to that entry. Changes no grid cells. Invariant test: every other colour's count unchanged; `total_stitches` drops by the background count.
- `substitute_colour`: `Params(from_dmc: str, to_dmc: str)`. Looks up `to_dmc` in `DMCPalette()`; raises `OpError` if unknown. Replaces the legend entry's DMCColor. If `to_dmc` already exists in the legend, behave as `merge_colours`. Grid unchanged in the plain case (test asserts identical grid).
- `merge_colours`: `Params(from_dmc: str, to_dmc: str)`. All cells of `from` → index of `to`; remove `from` from the legend; reindex; `background_index` follows. Test: no index ≥ len(legend); counts add up.
- `crop_pad`: `Params(width: int = 50, height: int = 50, anchor: Literal["center","fit_content","offset"]="fit_content", offset_x: int = 0, offset_y: int = 0, pad_dmc: str = "auto")`. `fit_content`: bounding box of non-background cells, centred in the target (if the box is larger than the target, crop the box centre). `center`: centre the current grid. `offset`: place the current grid's (0,0) at (offset_x, offset_y), negative allowed. Padding uses `background_index`; if None, `pad_dmc` (`auto` → add DMC 3865 Winter White to the legend and set it as background). Backstitch segments are translated by the same offset and clipped to the new bounds. Tests: fit_content preserves every non-background cell (count equality); translate moves backstitch; crop drops out-of-range segments.
- `outline_to_backstitch` (GROUP outline): `Params(outline_dmc: str = "auto", keep_cells: bool = False)`. `auto` = darkest legend entry by luminance. Step 1: compute the set O of outline cells. Step 2: backstitch = every unit edge between an O cell and a non-O cell **on the O cell's outer boundary** — i.e. edges where exactly one side is in O — then `merge_segments`-style merging of collinear runs (implement a small merge on `Segment`, shared in `xstitchlab/ops/_segments.py`, and reuse it in `generate_backstitch`). Step 3 (unless keep_cells): each O cell takes the majority colour among its 4-neighbours that are not in O, iterating until no O cells remain (cells with no non-O neighbour wait for the next pass; if a pass makes no progress, assign background). Remove the outline legend entry if unused. Tests: on a 7×7 grid with a 1-cell-wide black square ring around a 3×3 terracotta block on white, the result has no black cells, terracotta count grows by the ring's inner-adjacent share as per the majority rule (assert exact expected grid), and the backstitch is a closed ring (every corner touched has even degree).

Commit: `feat(ops): background_to_fabric, substitute_colour, merge_colours, crop_pad, outline_to_backstitch`.

---

### Task 6: Author a recipe for each of the five designs and turn the benchmark into a test ✅ DONE (bc62c1e)
**Depends on:** Tasks 3, 4, 5

> Outcome: 218 tests pass. Scores: Riga 0.906, Lübeck 0.954, Bergen 0.893, Tallinn 0.900, Gdańsk 0.783 (thresholds score−0.02 floored). All five design.json files are canonical with recipes and display titles; grid/legend/backstitch/background verified unchanged. Follow-up: the diff render paints fabric red when the candidate names it differently (score already ignores it).

**Files:**
- Modify: `designs/01-three-brothers-riga/design.json` … `designs/05-artus-gdansk/design.json` (add `recipe`, migrate to canonical shape via `Pattern.from_dict(...).to_dict()` — but keep `id`? No: drop `id`, `pipeline_stages`, `adjustment_stats`; the grid, legend, backstitch, and background must be byte-for-byte equivalent in meaning).
- Create: `tests/test_benchmark.py`
- Create: `docs/plans/2026-09-26-benchmark-log.md` (a table of what each recipe attempt scored; append, do not rewrite)

**Process (iterate, this is the tuning step)**

1. For each design, start from `PREDESIGNED` with `pixelate.width` = design width (45 for Riga, 50 for others; Lübeck's input is 1408×768, so use `crop_pad` to 50×50 with `fit_content` after pixelating at width 70) and `n_colors` = final colour count + 1 when the final has a fabric background that came from a sky colour.
2. Run `uv run xstitch benchmark designs/0X-*` and read `tools/benchmark_out/<slug>.png` and the confusion table.
3. Add `background_to_fabric`, `substitute_colour`, `merge_colours`, `crop_pad`, `outline_to_backstitch` calls with the parameters the research found (Lübeck: sky 813 → fabric, 357 → 3777; Bergen: 762 → 3072, 977 → 3830 roof; Tallinn: 3761 → fabric, outline 3371 → backstitch; Gdańsk: 813 → fabric, 502 → 3761, 3024 → 3866, 648 → 3024). The exact DMC codes the pipeline produces may differ from those in the research by MiniBatchKMeans seed; read them from the confusion table rather than assuming.
4. Stop when the score stops improving by more than 0.5 points over three attempts. Record each attempt in the log.
5. Write the recipe into `design.json` (`recipe` key) and save the canonical shape.

**Thresholds** in `tests/test_benchmark.py` (parametrised over the five folders): Riga ≥ 0.88, Lübeck ≥ 0.85, Tallinn ≥ 0.80, Bergen ≥ 0.70, Gdańsk ≥ 0.60. These are slightly below the design's targets so the test guards regressions without blocking on tuning luck; if a design scores higher, raise its threshold to (score − 0.02) and record it. If a design cannot reach its threshold, set the threshold to (achieved − 0.02), document why in the log, and flag it in the task report. Mark the test `@pytest.mark.slow` and make `uv run pytest tests/ -q` still run it (no deselect by default).

Verify: `uv run pytest tests/test_benchmark.py -q` passes and `uv run pytest tests/test_pattern_model.py -q` still passes on the rewritten JSONs.

Commit: `feat: recipes for the five Hanseatic designs and benchmark thresholds`.

---

### Task 7: Design folder library and `design.md` regeneration; export consolidation; delete dead code
**Depends on:** Task 1 (library part) and Task 4 (export part). Can start in parallel with Tasks 3–5 for the library part.

**Files:**
- Create: `xstitchlab/library/__init__.py`, `xstitchlab/library/design_folder.py`, `xstitchlab/library/design_md.py`
- Create: `xstitchlab/export/pattern_sheet.py` (merge of `pattern_sheet/generate.py` + `generate_a4.py` option B: `generate_pattern_sheet(pattern: Pattern, *, layout: Literal["a4","a5"]="a4", title: str, history: str = "", output_path: Path) -> Path`); move `template.html` next to it as `pattern_sheet_a5.html`; A4 HTML/CSS stays inline as it is today. `history` comes from `designs/<slug>/history.md` if present, else the A4 module's `HISTORY` dict keyed by slug fragment (move that dict into `history.md` files in each of the five folders and delete the dict).
- Create: `xstitchlab/export/threads.py`: `estimate(pattern) -> list[dict]` with keys `dmc_code, name, rgb, stitch_count, meters, skeins, skeins_decimal, sections_60cm, is_background, is_backstitch` (fixes the KeyError bug at its root; backstitch row uses total unit length in cm ÷ 60, 1 strand).
- Modify: `xstitchlab/core/visualizer.py`, `xstitchlab/export/png_exporter.py`, `xstitchlab/export/pdf_exporter.py`: any background detection uses `pattern.background_index`; add backstitch overlay to `render_color_preview` when `pattern.backstitch` is non-empty (reuse `backstitch.render_backstitch`).
- Delete: `xstitchlab/core/ai_generator.py`, `xstitchlab/export/pattern_sheet/` (both generators and `__init__`), `designs/outputs/designs/generate_hampshire_sheet.py` (untracked; leave it, it is the user's file — instead add a `history.md` next to `3_hampshire_rise_spring.json` is out of scope; skip Hampshire entirely), `image_input.preprocess_image/resize_for_preview/create_thumbnail`, `pixelator.pixelate_predesigned/snap_to_dominant_colors/quantize_then_resize/two_step_resize`, `ColorMapper.map_image/reduce_to_max_colors/get_substitutes`, `cli.py` `generate` command and `prompts` import of openai. Keep `prompts/templates.py` and the `prompt` command.
- Modify: `xstitchlab/cli.py`: `export <design_dir> --kind sheet|pdf|png-color|png-symbol|png-realistic|json [--layout a4|a5]`, `estimate <design_dir_or_json>` uses `export/threads.py`.
- Fix/migrate: `tests/test_integration.py::test_end_to_end_pipeline` and `tests/test_thread_calc.py::test_quick_estimate` — read the failures, fix the test if the expectation is stale or the code if it is a real bug, and say which in the commit.
- Test: `tests/test_design_folder.py`, `tests/test_design_md.py`, `tests/test_threads.py`, `tests/test_pattern_sheet.py`

**DesignFolder API**

```python
class DesignFolder:
    def __init__(self, root: Path, slug: str)
    @staticmethod
    def list(root: Path) -> list["DesignFolder"]   # sorted by slug; only dirs with prompt.md or input.png or design.json; skips names starting with "_" or "outputs"
    @staticmethod
    def create(root: Path, slug: str, title: str) -> "DesignFolder"   # validates slug ^[a-z0-9][a-z0-9-]*$, writes design.md stub with title
    path: Path; slug: str
    title -> str   # from design.json metadata.title, else design.md first heading, else slug
    has_input / has_pattern / has_prompt -> bool
    read_prompt() -> str; write_prompt(text)
    read_input() -> PIL.Image; write_input(bytes)
    read_pattern() -> Pattern; write_pattern(pattern)   # atomic: write design.json.tmp then os.replace; then regenerate design.md
    export_path(kind: str, layout: str | None = None) -> Path   # e.g. preview_color.png, preview_symbol.png, preview_realistic.png, pattern.pdf, pattern_sheet_a4.html, design.json
    summary() -> dict  # {slug, title, has_input, has_prompt, has_pattern, width, height, colors, stitches}
def default_root() -> Path   # env XSTITCH_DESIGNS_DIR or <repo>/designs
```

`design_md.render(pattern, folder) -> str` reproduces the current `design.md` layout (header, stats table, thread table with 60 cm sections, background note, label text if present). Preserve the "Label Text" and "Design Files" sections from an existing design.md by copying everything after the thread table's trailing note verbatim (split on the `## Label Text` heading). Test: rendering the five committed designs yields the same stitch numbers as the committed design.md thread tables (parse both; compare the `Stitches` column).

Verify: `uv run pytest tests/ -q` → 0 failures. `uv run xstitch export designs/01-three-brothers-riga --kind sheet` writes `pattern_sheet_a4.html`; open it and compare visually with the committed one (screenshot both with a headless Chrome if available: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --screenshot=... --window-size=1400,1000 file://...`).

Commit: `refactor: design folder library, merged pattern sheet, thread estimates with backstitch; remove dead code`.

---

### Task 8: Backend rewrite on the library and registry
**Depends on:** Tasks 3, 5, 7

**Files:**
- Modify: `pyproject.toml` root → add `[tool.uv.workspace] members = ["backend"]`; `backend/pyproject.toml` → `dependencies += ["xstitchlab"]` with `[tool.uv.sources] xstitchlab = { workspace = true }`. Remove `sys.path` lines from backend. Update `run-backend.sh`/`run-dev.sh` to `uv run uvicorn backend.app.main:app --reload --port 8000`.
- Delete: `backend/app/services/pattern_service.py`, `backend/app/routes/patterns.py`, `backend/app/routes/export.py`, `backend/app/schemas/patterns.py`
- Create: `backend/app/routes/designs.py`, `backend/app/routes/ops.py`, `backend/app/schemas.py`, `backend/app/deps.py` (`get_root()` from `XSTITCH_DESIGNS_DIR` or default), `backend/app/previews.py` (`pattern_to_png_b64(pattern, max_px=400)`)
- Modify: `backend/app/main.py` (mount routers, CORS for localhost:5173, `/api/health`)
- Test: `backend/tests/conftest.py` (copies `designs/01-three-brothers-riga` into a tmp root, sets env, yields `TestClient`), `backend/tests/test_designs.py`, `backend/tests/test_ops.py`, `backend/tests/test_exports.py`. Add `httpx` and `pytest` to backend dev deps. Run with `uv run --package xstitchlab-backend pytest backend/tests -q` (or from the root if the workspace resolves; document the working command in DEVELOPMENT.md).

**Routes** exactly as the design doc table. Schemas (pydantic): `DesignSummary`, `DesignDetail {slug,title,prompt,has_input,pattern: dict|None}`, `RunRequest {recipe: list[OpCall-shaped dict]}`, `RunResponse {pattern, steps: [{name, params, preview_png, stats}]}`, `ApplyRequest {pattern, op, params}`, `SavePattern {pattern}`. `OpError` → 400 `{detail, step_index, op}`; `ValidationError` from Params → 422. `GET /api/designs/{slug}/export/{kind}` writes the file into the folder via `export_path` and returns it with the right media type; `sheet` accepts `?layout=a4|a5`.

**Tests**: list shows the seeded design; detail returns its pattern with `recipe`; `PUT /input` then `POST /run` with `{"recipe": DEFAULTS["predesigned"]}` returns steps with previews and a pattern of width 50; `POST /ops/apply` with `background_to_fabric` returns a pattern with `background_index` set; `PUT /designs/{slug}` writes design.json and design.md; `GET /threads` returns rows including one with `is_backstitch`; `GET /export/sheet` returns HTML containing the title; 404 for unknown slug; 400 with `step_index` for a recipe with a pattern op first.

Commit: `feat(backend): design library, ops schemas, recipe run and apply, exports`.

---

### Task 9: Frontend scaffold — React + TypeScript, API client, Library page, read-only Editor canvas
**Depends on:** Task 8

**Files:**
- Delete: `frontend/src/main.js`, `frontend/src/editor/`, `frontend/src/state/`, `frontend/src/api/client.js`, `frontend/styles/`, old `frontend/index.html` content
- Create: `frontend/package.json` (react, react-dom, react-router-dom, zustand; dev: typescript, @types/react, @types/react-dom, @vitejs/plugin-react, vitest, @testing-library/react, jsdom, @playwright/test), `frontend/tsconfig.json`, `frontend/vite.config.ts` (proxy `/api` → 8000, react plugin, vitest `environment: jsdom`), `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx` (router: `/` Library, `/d/:slug` Editor)
- Create: `frontend/src/api/types.ts` (Pattern, LegendEntry, Segment, OpCall, OpSchema, RunResponse, DesignSummary, DesignDetail — mirror the backend JSON exactly), `frontend/src/api/client.ts` (one typed function per route, throws `ApiError {status, detail, step_index?, op?}`)
- Create: `frontend/src/model/grid.ts` (`cloneGrid`, `floodFill(grid, x, y, value) -> Change[]`, `rectCells`, `moveRect(grid, rect, dx, dy, fill) -> Change[]`), `frontend/src/model/segments.ts` (`key(seg)`, `normalise`, `splitToUnits`, `mergeCollinear`), `frontend/src/model/threads.ts` (client-side estimate identical to the backend formula for live display: 2 strands, 14 count, 1.15 margin, 8 m skein, 60 cm sections)
- Create: `frontend/src/store/editorStore.ts` (zustand: `design`, `pattern`, `recipe`, `steps`, `selectedColor`, `tool`, `selection`, `zoom`, `dirty`; actions `load(slug)`, `setCells(changes)`, `setBackstitch(add[], remove[])`, `setBackground(i)`, `undo`, `redo`, `pushHistory(patch)` with a `HistoryPatch = {cells: Change[], backstitchAdd: Segment[], backstitchRemove: Segment[]}` and a 200-entry cap)
- Create: `frontend/src/canvas/LayeredRenderer.ts` (class holding 4 offscreen canvases: cells, grid lines, backstitch, overlay; `setPattern`, `setViewMode('color'|'symbol')`, `markDirty(cells)`, `draw(ctx, view)` composes with the current zoom/pan; symbol text only when cell px ≥ 14) and `frontend/src/canvas/PatternCanvas.tsx` (one `<canvas>`, `ResizeObserver`, wheel zoom about the cursor, space-drag or middle-drag pan, `F` zoom-to-fit, exposes `toCell(clientX, clientY)` and `toEdge(...)`)
- Create: `frontend/src/pages/Library.tsx` (cards from `GET /api/designs`, thumbnail from `preview_png`, "New design" form with slug+title), `frontend/src/pages/Editor.tsx` (three-column shell; left = placeholder "Recipe" panel, centre = canvas, right = `PalettePanel` listing legend swatches with DMC code/name/count and `ThreadPanel` from `model/threads.ts`)
- Test: `frontend/src/model/grid.test.ts`, `segments.test.ts`, `threads.test.ts`, `store/editorStore.test.ts` (setCells + undo + redo round trip; history cap)

Verify: `npm run build` passes typecheck; `npm test` green; with backend running, `/` lists designs and `/d/01-three-brothers-riga` renders the pattern with backstitch and the palette.

Commit: `feat(frontend): React scaffold, typed API client, library page, layered canvas`.

---

### Task 10: Recipe panel with schema-driven cards, run, and step previews
**Depends on:** Task 9

**Files:**
- Create: `frontend/src/components/RecipePanel.tsx`, `OpCard.tsx`, `ParamField.tsx`, `AddOpMenu.tsx`, `StepStrip.tsx`
- Modify: `editorStore.ts` (`opSchemas`, `recipe` edits: `addOp(name, atIndex)`, `removeOp(i)`, `moveOp(i, j)`, `setParam(i, key, value)`, `runRecipe()` → calls `POST /run`, replaces `pattern` and `steps`, clears history, sets `dirty=false`; `loadDefaults(name)`), `Editor.tsx`
- Test: `frontend/src/components/ParamField.test.tsx` (renders integer, boolean, enum, string fields from JSON Schema and emits changes), `store/recipe.test.ts` (add/remove/move/setParam; runRecipe replaces pattern — mock the client)

**ParamField** maps JSON Schema: `integer`/`number` with `minimum/maximum` → number input (+ slider when both bounds exist), `boolean` → switch, `enum` → segmented control if ≤ 4 options else select, `string` → text input; `anyOf` with `null` → the inner type with a "default" checkbox. Field label = `title` or humanised key; `description` as helper text.

**RecipePanel**: header with "Default: predesigned | photo" chooser, the ordered list of `OpCard`s (drag to reorder or up/down buttons, remove, collapsible), "Add operation" menu grouped by `group`, a "Run" button (disabled while running, shows spinner) and unsaved-edits confirmation if `dirty`. Errors from `POST /run` show on the failing card (via `step_index`) or as a toast for validation.

**StepStrip**: horizontal thumbnails of `steps[i].preview_png` with name and stats; clicking one shows it as a read-only overlay on the canvas (a `previewStep` index in the store; the renderer draws the PNG scaled to the grid instead of cells); clicking the last or pressing Esc returns to the editable pattern. J/K move between steps.

Verify manually: open Riga, load its recipe, Run, see steps, change `n_colors`, Run again.

Commit: `feat(frontend): schema-driven recipe panel with run and step previews`.

---

### Task 11: Editing tools, undo, keyboard, palette actions, save
**Depends on:** Task 10

**Files:**
- Create: `frontend/src/components/Toolbar.tsx`, `frontend/src/canvas/tools/{paint,fill,select,eyedropper,backstitch}.ts` (each tool: `onDown/onMove/onUp(ev, ctx)` producing `HistoryPatch`es), `frontend/src/components/PaletteMenu.tsx` (context menu on a swatch: Replace with DMC… (searchable list from `data/dmc_colors.json` served at `GET /api/dmc`), Merge into…, Set as fabric), `frontend/src/components/SaveButton.tsx`, `frontend/src/components/ConfirmDialog.tsx`, `frontend/src/hooks/useShortcuts.ts`
- Backend: add `GET /api/dmc` → the palette list (small addition in `routes/ops.py`, with a test)
- Modify: `editorStore.ts` (`applyOp(call)` → `POST /ops/apply`, pushes a whole-grid patch to history; `save()` → `PUT /designs/{slug}`), `PatternCanvas.tsx` (dispatch pointer events to the active tool; selection marquee and move-preview on the overlay layer), `PalettePanel.tsx`
- Test: `canvas/tools/fill.test.ts`, `select.test.ts` (move produces the right cell changes and clears the source with background), `store/applyOp.test.ts` (mock client; undo restores the previous grid and legend), `hooks/useShortcuts.test.ts`

**Tools and keys**: B paint, G fill, M rectangle select, I eyedropper, L backstitch line (drag along edges; click toggles one unit edge), 1–9 select colour, Delete clears the selection to fabric, arrows nudge the selection by one cell, Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z / Ctrl+Y redo, Ctrl/Cmd+S save, F fit, +/- zoom, Esc clears selection/preview. Show a `?` overlay listing them.

Live thread panel: recomputes from the store on every pattern change (memoised on `pattern` reference).

Commit: `feat(frontend): editing tools, undo/redo, palette actions, save`.

---

### Task 12: Brief panel, input upload, exports, and the "New design" flow
**Depends on:** Task 11

**Files:**
- Create: `frontend/src/components/BriefPanel.tsx` (prompt textarea with "Insert Hanseatic template" — template text fetched from `GET /api/prompt-template` (add to backend: returns `prompts/templates.py` pixel-art template rendered with a placeholder subject; test), Copy button, drop zone for input.png with preview and "Replace"), `frontend/src/components/ExportMenu.tsx` (buttons for each export kind; opens the returned file in a new tab for HTML/PDF, downloads PNG/JSON), `frontend/src/components/EmptyState.tsx` for a design without input or pattern
- Modify: `Editor.tsx` (tabs on the left: Brief | Recipe; Editor shows EmptyState guidance until a pattern exists), `Library.tsx` (new design → navigates to its Brief tab)

Verify manually: create `99-test-design`, paste a prompt, drop `designs/13-salzspeicher-lubeck/input.png`, run the predesigned recipe, save, export sheet. Then delete the test folder.

Commit: `feat(frontend): brief panel, input upload, exports`.

---

### Task 13: Visual design pass
**Depends on:** Task 12. Use the `frontend-design:frontend-design` skill before writing CSS.

**Files:**
- Create: `frontend/src/styles/tokens.css` (light default: Aida cream ground `#f6f1e7`, ink `#1f1b16`, terracotta accent `#c8624a` (DMC 3830), muted sage `#96a07e` (DMC 522) for secondary, borders in warm grey; dark palette under `@media (prefers-color-scheme: dark)` and `[data-theme=dark]`), `frontend/src/styles/base.css`, component styles co-located as CSS modules
- Fonts: one display serif (Fraunces or similar via Google Fonts) for page and design titles, Inter for UI, JetBrains Mono for DMC codes and counts
- Layout: resizable side panels (drag handle, min 280px, persisted in localStorage), cards with 12px radius and hairline borders instead of `<details>`, swatches 32px with the DMC code beneath, toolbar as a vertical rail on the canvas's left edge, status toasts bottom-centre
- Keep it functional at 1024px wide; below that, stack panels under the canvas

Verify with screenshots of Library and Editor (light and dark) saved to `docs/screenshots/` and referenced from README.

Commit: `style(frontend): workshop theme, tokens, resizable panels`.

---

### Task 14: Playwright smoke, scripts, docs, cleanup
**Depends on:** Task 13

**Files:**
- Create: `frontend/e2e/smoke.spec.ts` (starts against a backend with `XSTITCH_DESIGNS_DIR` pointing to a temp copy of `designs/01-three-brothers-riga`: open library → open Riga → Run → paint one cell → Save → reload → the cell persists), `frontend/playwright.config.ts`, npm script `e2e`
- Modify: `run-dev.sh`, `run-backend.sh`, `run-frontend.sh`, `README.md`, `DEVELOPMENT.md` (commands: `uv run pytest`, backend tests, `npm test`, `npm run e2e`, `xstitch run/export/benchmark`), `CLAUDE.md` project section (structure and commands only), `docs/features.md` (drop the *(new)* markers)
- Delete: anything left in `frontend/` from the old app, `xstitchlab/core/adjuster.AdjustmentSettings/adjust_pattern/indices_to_image` if unused (`grep -rn adjust_pattern`), `backend/.venv` from git if tracked (check `.gitignore`)

Verify: `uv run pytest tests/ -q` and backend tests green; `npm test` green; `npm run e2e` green; `./run-dev.sh` starts both.

Commit: `chore: e2e smoke, scripts, docs`.

---

## Review
- [ ] Code review requested (tomek-superpowers:request-review) after Task 8 (backend complete) and after Task 14
- [ ] All feedback addressed
- [ ] Final verification passed (tomek-superpowers:verify)
