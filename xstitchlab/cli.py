"""CLI interface for XStitchLab."""

import json as jsonlib
import typer
from pathlib import Path
from typing import Optional
from PIL import Image
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.image_input import load_image, get_image_info
from .core.pattern import OpCall, Pattern, DMCPalette
from .export.png_exporter import PNGExporter
from .library import DesignFolder, LibraryError
from .ops import registry
from .ops.base import OpError, RunResult
from .ops.defaults import DEFAULTS, default_recipe, with_overrides

app = typer.Typer(
    name="xstitch",
    help="XStitchLab - Cross-stitch pattern generation tool",
    add_completion=False
)
console = Console()

EXPORT_KINDS = ("sheet", "pdf", "png-color", "png-symbol", "png-realistic", "json")


def _run(image_path: Path, recipe: list[OpCall], title: Optional[str] = None) -> tuple[RunResult, Image.Image]:
    """Load an image, fold the recipe over it, fill in title/source. Exits on OpError."""
    original = load_image(image_path)
    try:
        result = registry.run_recipe(original, recipe)
    except OpError as e:
        where = f" (step {e.step_index}: {e.op})" if e.step_index is not None else ""
        console.print(f"[red]Recipe failed{where}: {e}[/red]")
        raise typer.Exit(1)
    pattern = result.pattern
    if not pattern.metadata.title:
        pattern.metadata.title = title or image_path.stem
    pattern.metadata.source_image = str(image_path)
    return result, original


def _last_image(result: RunResult) -> Optional[Image.Image]:
    """The image produced by the last image-stage step (what `convert` shows as 'pixelated')."""
    images = [s.result for s in result.steps if isinstance(s.result, Image.Image)]
    return images[-1] if images else None


def _print_steps(result: RunResult) -> None:
    table = Table(title="Recipe steps")
    table.add_column("#", justify="right", style="dim")
    table.add_column("op", style="cyan")
    table.add_column("params")
    table.add_column("stats")
    for i, step in enumerate(result.steps):
        params = ", ".join(f"{k}={v}" for k, v in step.params.items()) or "-"
        stats = ", ".join(f"{k}={v}" for k, v in step.stats.items())
        table.add_row(str(i), step.name, params, stats)
    console.print(table)


def _load_recipe_file(path: Path) -> list[OpCall]:
    """A JSON list of {op, params}, or a design.json whose `recipe` key holds one."""
    data = jsonlib.loads(path.read_text())
    if isinstance(data, dict):
        data = data.get("recipe") or []
    if not isinstance(data, list) or not data:
        raise typer.BadParameter(f"{path}: no recipe found")
    return [OpCall.from_dict(c) for c in data]


def _resolve_recipe(source: Path, recipe: Optional[str]) -> list[OpCall]:
    if recipe is not None:
        if recipe in DEFAULTS:
            return default_recipe(recipe)
        recipe_path = Path(recipe)
        if not recipe_path.is_file():
            raise typer.BadParameter(f"--recipe must be one of {sorted(DEFAULTS)} or a JSON file, got {recipe!r}")
        return _load_recipe_file(recipe_path)
    design_json = source / "design.json" if source.is_dir() else None
    if design_json and design_json.is_file():
        stored = Pattern.from_json(design_json).recipe
        if stored:
            return stored
    return default_recipe("predesigned")


def _design_folder(design_dir: Path) -> DesignFolder:
    if not design_dir.is_dir():
        console.print(f"[red]{design_dir} is not a design directory[/red]")
        raise typer.Exit(1)
    design_dir = design_dir.resolve()
    return DesignFolder(design_dir.parent, design_dir.name)


def _load_pattern(path: Path) -> Pattern:
    """A design directory (its design.json) or a pattern JSON file."""
    try:
        return _design_folder(path).read_pattern() if path.is_dir() else Pattern.from_json(path)
    except LibraryError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def convert(
    image: Path = typer.Argument(
        ...,
        help="Path to input image (PNG, JPG, etc.)",
        exists=True
    ),
    size: int = typer.Option(
        40,
        "--size", "-s",
        help="Grid size (width in stitches)"
    ),
    colors: int = typer.Option(
        8,
        "--colors", "-c",
        help="Number of colors (max threads)"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory (defaults to current directory)"
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title", "-t",
        help="Pattern title"
    ),
    dither: bool = typer.Option(
        False,
        "--dither/--no-dither",
        help="Apply dithering for smoother gradients"
    ),
    lab: bool = typer.Option(
        True,
        "--lab/--rgb",
        help="Use CIELAB color space for better color matching"
    ),
    pdf: bool = typer.Option(
        False,
        "--pdf",
        help="Also export PDF pattern"
    ),
    json: bool = typer.Option(
        False,
        "--json",
        help="Also export pattern data as JSON"
    )
):
    """Convert an image to a cross-stitch pattern (the `photo` recipe)."""
    console.print(f"\n[bold blue]XStitchLab[/bold blue] - Converting {image.name}\n")

    # Show input info
    info = get_image_info(image)
    console.print(f"  Input: {info['width']}×{info['height']} pixels, {info['format']}")
    console.print(f"  Target: {size}×{int(size * info['height'] / info['width'])} stitches, {colors} colors\n")

    recipe = default_recipe("photo", width=size, n_colors=colors)
    for call in recipe:
        if call.op == "quantize_image":
            call.params["dither"] = dither
        if call.op == "pixelate":
            call.params["color_space"] = "lab" if lab else "rgb"

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Running recipe...", total=None)
        result, original = _run(image, recipe, title)
    pattern, pixelated = result.pattern, _last_image(result)

    # Set up output
    output_dir = output or Path.cwd()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = title or image.stem

    # Export PNG files
    exporter = PNGExporter(output_dir)
    exports = exporter.export_all(pattern, base_name, original, pixelated)

    console.print("\n[green]✓[/green] Pattern created successfully!\n")

    # Show pattern info
    table = Table(title="Pattern Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Dimensions", f"{pattern.metadata.width}×{pattern.metadata.height} stitches")
    table.add_row("Colors", str(pattern.metadata.color_count))
    table.add_row("Total Stitches", f"{pattern.metadata.total_stitches:,}")
    table.add_row("Difficulty", pattern.metadata.difficulty.capitalize())
    table.add_row("Fabric (14ct)", f"{pattern.metadata.fabric_width_inches:.1f}\"×{pattern.metadata.fabric_height_inches:.1f}\"")

    console.print(table)

    # Show color legend
    console.print("\n[bold]Thread List:[/bold]")
    for entry in pattern.legend:
        console.print(
            f"  {entry.symbol}  DMC {entry.dmc_color.code:6} - {entry.dmc_color.name} ({entry.stitch_count:,} stitches)"
        )

    # Export JSON if requested
    if json:
        json_path = output_dir / f"{base_name}.json"
        pattern.to_json(json_path)
        exports["json"] = json_path

    # Export PDF if requested
    if pdf:
        from .export.pdf_exporter import PDFExporter
        exports["pdf"] = PDFExporter(output_dir).export_pattern(pattern, base_name)

    # Show exported files
    console.print("\n[bold]Exported Files:[/bold]")
    for name, path in exports.items():
        console.print(f"  • {name}: {path}")

    console.print()


@app.command()
def info(
    image: Path = typer.Argument(
        ...,
        help="Path to image file",
        exists=True
    )
):
    """Show information about an image file."""
    info = get_image_info(image)

    table = Table(title=f"Image Info: {info['filename']}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Path", str(info['path']))
    table.add_row("Format", info['format'])
    table.add_row("Mode", info['mode'])
    table.add_row("Size", f"{info['width']}×{info['height']} pixels")
    table.add_row("Aspect Ratio", str(info['aspect_ratio']))

    console.print(table)

    # Suggest grid sizes
    console.print("\n[bold]Suggested Grid Sizes:[/bold]")
    for size in [30, 40, 60, 80, 100]:
        height = int(size * info['height'] / info['width'])
        console.print(f"  --size {size}: {size}×{height} stitches")


@app.command()
def prompt(
    text: str = typer.Argument(
        ...,
        help="Your prompt to enhance"
    ),
    style: str = typer.Option(
        "simple",
        "--style", "-s",
        help="Style preset to apply"
    ),
    list_styles: bool = typer.Option(
        False,
        "--list",
        help="List all available styles"
    )
):
    """Preview how your prompt will be enhanced for cross-stitch generation.

    This shows the full prompt to paste into an external image generator.
    """
    from .prompts.templates import get_template, list_styles as get_styles, get_style_description

    if list_styles:
        console.print("\n[bold]Available Style Presets:[/bold]\n")
        for style_name in get_styles():
            desc = get_style_description(style_name)
            console.print(f"  [cyan]{style_name:12}[/cyan] - {desc[:60]}...")
        console.print()
        return

    enhanced = get_template(style, text)

    console.print("\n[bold]Prompt Enhancement Preview[/bold]\n")

    console.print("[dim]Your prompt:[/dim]")
    console.print(f"  {text}\n")

    console.print(f"[dim]Style:[/dim] [cyan]{style}[/cyan]\n")

    console.print("[dim]Enhanced prompt:[/dim]")
    console.print(f"  [green]{enhanced}[/green]\n")


@app.command()
def run(
    path: Path = typer.Argument(..., help="Design directory (uses input.png inside) or an image file", exists=True),
    recipe: Optional[str] = typer.Option(
        None, "--recipe", "-r",
        help=f"Default recipe name ({', '.join(DEFAULTS)}) or a JSON file (a list of steps, or a design.json with a recipe). "
             "Default: the design's own recipe, else 'predesigned'.",
    ),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output JSON (default: <dir>/run.json or <stem>_pattern.json)"),
    width: Optional[int] = typer.Option(None, "--width", "-w", help="Override `width` on every op that has it"),
    colors: Optional[int] = typer.Option(None, "--colors", "-c", help="Override `n_colors` on every op that has it"),
):
    """Run a recipe over an image and write the resulting pattern JSON."""
    if path.is_dir():
        image_path = path / "input.png"
        if not image_path.is_file():
            console.print(f"[red]{path} has no input.png[/red]")
            raise typer.Exit(1)
        out = out or path / "run.json"
        title = path.name
    else:
        image_path = path
        out = out or path.with_name(f"{path.stem}_pattern.json")
        title = path.stem

    steps = with_overrides(_resolve_recipe(path, recipe), width=width, n_colors=colors)
    result, _ = _run(image_path, steps, title)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(jsonlib.dumps(result.pattern.to_dict(), indent=2))
    _print_steps(result)
    console.print(f"[green]✓[/green] Wrote {out}")


@app.command()
def benchmark(
    dirs: Optional[list[Path]] = typer.Argument(None, help="Design directories (default: designs/0*)"),
    out_dir: Path = typer.Option(Path("tools/benchmark_out"), "--out-dir", help="Where side-by-side PNGs go"),
    render: bool = typer.Option(True, "--render/--no-render", help="Write side-by-side PNGs"),
):
    """Score each design's recipe against its committed final pattern."""
    from tools.benchmark import main as benchmark_main

    design_dirs = list(dirs or []) or sorted(p for p in Path("designs").glob("0*") if p.is_dir())
    if not design_dirs:
        console.print("[red]No design directories found[/red]")
        raise typer.Exit(1)
    benchmark_main(design_dirs, out_dir=out_dir, render=render)


@app.command()
def palette():
    """Show available DMC thread colors."""
    dmc = DMCPalette()

    console.print(f"\n[bold]DMC Thread Palette[/bold] ({len(dmc)} colors)\n")

    # Show first 50 colors as example
    table = Table()
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("RGB", style="dim")

    for i, color in enumerate(dmc.colors[:50]):
        rgb_str = f"({color.rgb[0]:3}, {color.rgb[1]:3}, {color.rgb[2]:3})"
        table.add_row(color.code, color.name, rgb_str)

    console.print(table)
    console.print(f"\n... and {len(dmc) - 50} more colors")


@app.command()
def estimate(
    path: Path = typer.Argument(..., help="Design directory or pattern JSON file", exists=True),
    fabric_count: Optional[int] = typer.Option(None, "--fabric", "-f", help="Aida fabric count (default: the pattern's, usually 14)"),
):
    """Thread per colour: length, skeins, and 60cm kit sections (backstitch included)."""
    from .export import threads

    pattern = _load_pattern(path)
    rows = threads.estimate(pattern, fabric_count=fabric_count)
    total = threads.totals(rows)
    count = fabric_count or pattern.metadata.fabric_count

    console.print(f"\n[bold]Thread Estimates for {pattern.metadata.title}[/bold]\n")
    console.print(f"Fabric: {count}-count Aida")
    console.print(f"Size: {pattern.width}×{pattern.height} stitches, {total['stitches']:,} stitched\n")

    table = Table(title="Shopping List")
    table.add_column("DMC", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Stitches", justify="right")
    table.add_column("Thread", justify="right")
    table.add_column("Skeins", justify="right")
    table.add_column("60cm sections", justify="right")

    for row in rows:
        if row["is_background"]:
            table.add_row(row["dmc_code"], f"{row['name']} [dim](fabric, not stitched)[/dim]", f"{row['stitch_count']:,}", "-", "-", "-")
            continue
        stitches = f"{row['stitch_count']:,}" + (" segs" if row["is_backstitch"] else "")
        table.add_row(
            row["dmc_code"], row["name"], stitches,
            f"{row['meters'] * 100:.0f}cm", str(row["skeins"]), str(row["sections_60cm"]),
        )
    table.add_row("", "[bold]Total[/bold]", "", f"[bold]{total['meters']:.1f}m[/bold]",
                  f"[bold]{total['skeins']}[/bold]", f"[bold]{total['sections_60cm']}[/bold]")
    console.print(table)


def _export(design_dir: Path, kind: str, layout: Optional[str]) -> Path:
    if kind not in EXPORT_KINDS:
        raise typer.BadParameter(f"--kind must be one of {', '.join(EXPORT_KINDS)}, got {kind!r}")
    folder = _design_folder(design_dir)
    try:
        pattern = folder.read_pattern()
        out = folder.export_path(kind, layout)
    except LibraryError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if kind == "sheet":
        from .export.pattern_sheet import generate_pattern_sheet
        generate_pattern_sheet(
            pattern, layout=layout or "a4", title=folder.title,
            history=folder.read_history(), output_path=out,
        )
    elif kind == "pdf":
        from .export.pdf_exporter import quick_export_pdf
        quick_export_pdf(pattern, out)
    elif kind == "json":
        folder.write_pattern(pattern)
    else:
        from .core.visualizer import render_color_preview, render_symbol_grid, render_thread_realistic
        render = {
            "png-color": render_color_preview,
            "png-symbol": render_symbol_grid,
            "png-realistic": render_thread_realistic,
        }[kind]
        render(pattern).save(out, "PNG")
    return out


@app.command()
def export(
    design_dir: Path = typer.Argument(..., help="Design directory (designs/<slug>)", exists=True),
    kind: str = typer.Option("sheet", "--kind", "-k", help=f"One of: {', '.join(EXPORT_KINDS)}"),
    layout: Optional[str] = typer.Option(None, "--layout", "-l", help="Sheet layout: a4 (default) or a5"),
):
    """Write one export into the design directory (see DesignFolder.export_path for names).

    Sheets take their story text from <design_dir>/history.md when present.
    """
    out = _export(design_dir, kind, layout)
    console.print(f"[green]✓[/green] Wrote {out}")
    if kind == "sheet":
        console.print(f"  Open in Chrome → Cmd+P → {(layout or 'a4').upper()} → No margins → Background graphics → Save as PDF")


@app.command("pattern-sheet")
def pattern_sheet(
    design_dir: Path = typer.Argument(..., help="Design directory (designs/<slug>)", exists=True),
    layout: Optional[str] = typer.Option(None, "--layout", "-l", help="Sheet layout: a4 (default) or a5"),
):
    """Alias of `export --kind sheet`."""
    export(design_dir, "sheet", layout)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
