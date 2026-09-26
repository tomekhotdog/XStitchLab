"""Score a recipe's output against each design's committed final pattern.

Usage: `xstitch benchmark [DIRS...]` or `uv run python -m tools.benchmark`.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw
from rich.console import Console
from rich.table import Table

from xstitchlab.core.image_input import load_image
from xstitchlab.core.pattern import OpCall, Pattern
from xstitchlab.core.visualizer import get_font
from xstitchlab.ops import registry
from xstitchlab.ops.base import OpError
from xstitchlab.ops.defaults import default_recipe

FABRIC = (245, 240, 235)
DIFF = (230, 30, 30)
LABEL_H = 24
GAP = 12


def score(candidate: Pattern, final: Pattern) -> dict:
    """{'exact': fraction of cells whose DMC code matches, 'size_ok': bool,
    'confusion': {(cand_dmc, final_dmc): count} (only mismatches), 'diff_cells': int}.
    If sizes differ: exact=0.0, size_ok=False, confusion={}, diff_cells=None."""
    if (candidate.width, candidate.height) != (final.width, final.height):
        return {"exact": 0.0, "size_ok": False, "confusion": {}, "diff_cells": None}
    cand_codes = _codes(candidate)
    final_codes = _codes(final)
    confusion: dict[tuple[str, str], int] = {}
    diff = 0
    for cand_row, final_row in zip(candidate.grid, final.grid):
        for c, f in zip(cand_row, final_row):
            key = (cand_codes[c], final_codes[f])
            if key[0] != key[1]:
                diff += 1
                confusion[key] = confusion.get(key, 0) + 1
    total = candidate.width * candidate.height
    return {"exact": (total - diff) / total, "size_ok": True, "confusion": confusion, "diff_cells": diff}


def benchmark_design(design_dir: Path, recipe: list[OpCall] | None = None) -> dict:
    """Run `recipe` (the design's own if None) on input.png and score it against design.json."""
    design_dir = Path(design_dir)
    final = Pattern.from_json(design_dir / "design.json")
    if recipe is None:
        recipe = final.recipe
    if not recipe:
        raise OpError(f"{design_dir.name}: design.json has no recipe and none was given")
    candidate = registry.run_recipe(load_image(design_dir / "input.png"), recipe).pattern
    s = score(candidate, final)
    top = sorted(s["confusion"].items(), key=lambda kv: -kv[1])[:10]
    return {
        "slug": design_dir.name,
        "exact": s["exact"],
        "size_ok": s["size_ok"],
        "cand_size": (candidate.width, candidate.height),
        "final_size": (final.width, final.height),
        "colors_final": len(final.legend),
        "colors_candidate": len(candidate.legend),
        "backstitch_final": len(final.backstitch),
        "backstitch_candidate": len(candidate.backstitch),
        "confusion": [[c, f, n] for (c, f), n in top],
        "candidate": candidate,
        "final": final,
    }


def render_side_by_side(input_img: Image.Image, candidate: Pattern, final: Pattern, path: Path, cell_px: int = 8) -> None:
    """input (scaled to final height) | candidate | final | diff (final with red cells where DMC differs)."""
    final_img = _render(final, cell_px)
    cand_img = _render(candidate, cell_px)
    diff_img = _render(final, cell_px, mismatch_against=candidate)
    scale = final_img.height / input_img.height
    input_scaled = input_img.convert("RGB").resize(
        (max(1, round(input_img.width * scale)), final_img.height), Image.Resampling.LANCZOS
    )
    panels = [("input", input_scaled), ("candidate", cand_img), ("final", final_img), ("diff", diff_img)]

    width = sum(p.width for _, p in panels) + GAP * (len(panels) + 1)
    height = max(p.height for _, p in panels) + LABEL_H + GAP * 2
    sheet = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    font = get_font(12)
    x = GAP
    for label, panel in panels:
        draw.text((x, GAP), label, fill=(0, 0, 0), font=font)
        sheet.paste(panel, (x, GAP + LABEL_H))
        x += panel.width + GAP
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, "PNG")


def main(design_dirs: list[Path], out_dir: Path = Path("tools/benchmark_out"), render: bool = True) -> list[dict]:
    """Benchmark each design dir, print a Rich table, and write <slug>.png per design when `render`."""
    console = Console()
    results = []
    for design_dir in design_dirs:
        design_dir = Path(design_dir)
        recipe, source = _recipe_for(design_dir)
        try:
            result = benchmark_design(design_dir, recipe)
        except OpError as e:
            console.print(f"[yellow]{design_dir.name}: skipped ({e})[/yellow]")
            continue
        result["recipe_source"] = source
        results.append(result)
        if render:
            out_path = Path(out_dir) / f"{design_dir.name}.png"
            render_side_by_side(load_image(design_dir / "input.png"), result["candidate"], result["final"], out_path)
            result["render"] = out_path

    table = Table(title="Recipe benchmark", caption="* = design.json has no recipe; scored with the predesigned default at the final's width")
    for col in ("design", "cand", "final", "col c/f", "bs c/f", "exact"):
        table.add_column(col, justify="right" if col == "exact" else "left", no_wrap=True)
    for r in results:
        exact = f"{r['exact'] * 100:.1f}%" if r["size_ok"] else "mismatch"
        slug = r["slug"] + ("" if r["recipe_source"] == "design" else " *")
        table.add_row(
            slug, "{}x{}".format(*r["cand_size"]), "{}x{}".format(*r["final_size"]),
            f"{r['colors_candidate']}/{r['colors_final']}",
            f"{r['backstitch_candidate']}/{r['backstitch_final']}", exact,
        )
    console.print(table)
    return results


def _recipe_for(design_dir: Path) -> tuple[list[OpCall] | None, str]:
    """(None, "design") when design.json carries a recipe; else the predesigned default at the final's width."""
    final = Pattern.from_json(design_dir / "design.json")
    if final.recipe:
        return None, "design"
    return default_recipe("predesigned", width=final.width), "default"


def _codes(pattern: Pattern) -> list[str]:
    return [entry.dmc_color.code for entry in pattern.legend]


def _render(pattern: Pattern, cell_px: int, mismatch_against: Pattern | None = None) -> Image.Image:
    """Flat colour blocks; background cells as fabric; mismatching cells (by DMC code) in red."""
    img = Image.new("RGB", (pattern.width * cell_px, pattern.height * cell_px), FABRIC)
    draw = ImageDraw.Draw(img)
    codes = _codes(pattern)
    other_codes = _codes(mismatch_against) if mismatch_against is not None else None
    same_size = mismatch_against is not None and (
        (mismatch_against.width, mismatch_against.height) == (pattern.width, pattern.height)
    )
    for y, row in enumerate(pattern.grid):
        for x, idx in enumerate(row):
            if same_size and codes[idx] != other_codes[mismatch_against.grid[y][x]]:
                color = DIFF
            elif idx == pattern.background_index:
                color = FABRIC
            else:
                color = pattern.legend[idx].dmc_color.rgb
            draw.rectangle([x * cell_px, y * cell_px, (x + 1) * cell_px - 1, (y + 1) * cell_px - 1], fill=color)
    return img


if __name__ == "__main__":
    dirs = [Path(a) for a in sys.argv[1:]] or sorted(p for p in Path("designs").glob("0*") if p.is_dir())
    main(dirs)
