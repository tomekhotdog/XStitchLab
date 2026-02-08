"""CLI interface for XStitchLab."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.image_input import load_image, get_image_info
from .core.pixelator import pixelate, get_color_indices
from .core.color_mapper import ColorMapper
from .core.pattern import Pattern, PatternMetadata, ColorLegendEntry, DMCPalette
from .core.visualizer import create_pattern_sheet
from .export.png_exporter import PNGExporter, quick_export

# Standard symbols for pattern display
SYMBOLS = [
    "●", "■", "▲", "◆", "★", "♦", "♣", "♠", "♥", "○",
    "□", "△", "◇", "☆", "◐", "◑", "◒", "◓", "⬟", "⬡",
    "⊕", "⊗", "⊙", "⊚", "⊛", "⊜", "⊝", "⧫", "⬢", "⬣",
    "▼", "◀", "▶", "▷", "◁", "⬤", "⬥", "⬦", "⬧", "⬨",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"
]

app = typer.Typer(
    name="xstitch",
    help="XStitchLab - Cross-stitch pattern generation tool",
    add_completion=False
)
console = Console()


def create_pattern_from_image(
    image_path: Path,
    grid_size: int,
    n_colors: int,
    use_dithering: bool,
    use_lab_colors: bool,
    title: Optional[str] = None
) -> tuple[Pattern, "Image.Image", "Image.Image"]:
    """Core pipeline: image → pixelate → map → pattern."""
    from PIL import Image

    # Load and process image
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Load image
        task = progress.add_task("Loading image...", total=None)
        original = load_image(image_path)
        progress.update(task, completed=True)

        # Pixelate
        task = progress.add_task("Pixelating image...", total=None)
        pixelated, palette = pixelate(
            original,
            grid_width=grid_size,
            n_colors=n_colors,
            use_dithering=use_dithering
        )
        progress.update(task, completed=True)

        # Map colors to DMC
        task = progress.add_task("Mapping to DMC colors...", total=None)
        mapper = ColorMapper(use_lab=use_lab_colors)
        dmc_colors = mapper.map_palette(palette)
        progress.update(task, completed=True)

        # Build pattern
        task = progress.add_task("Building pattern...", total=None)
        color_indices = get_color_indices(pixelated, palette)

        # Create legend entries with symbols
        legend = []
        for i, dmc in enumerate(dmc_colors):
            symbol = SYMBOLS[i] if i < len(SYMBOLS) else str(i)
            legend.append(ColorLegendEntry(
                dmc_color=dmc,
                symbol=symbol,
                stitch_count=0
            ))

        # Create pattern
        metadata = PatternMetadata(
            title=title or image_path.stem,
            source_image=str(image_path)
        )
        pattern = Pattern(
            grid=color_indices.tolist(),
            legend=legend,
            metadata=metadata
        )
        pattern.count_stitches()
        progress.update(task, completed=True)

    return pattern, original, pixelated


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
    """Convert an image to a cross-stitch pattern."""
    console.print(f"\n[bold blue]XStitchLab[/bold blue] - Converting {image.name}\n")

    # Show input info
    info = get_image_info(image)
    console.print(f"  Input: {info['width']}×{info['height']} pixels, {info['format']}")
    console.print(f"  Target: {size}×{int(size * info['height'] / info['width'])} stitches, {colors} colors\n")

    # Create pattern
    pattern, original, pixelated = create_pattern_from_image(
        image,
        grid_size=size,
        n_colors=colors,
        use_dithering=dither,
        use_lab_colors=lab,
        title=title
    )

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
        try:
            from .export.pdf_exporter import PDFExporter
            pdf_exporter = PDFExporter(output_dir)
            pdf_path = pdf_exporter.export_pattern(pattern, base_name)
            exports["pdf"] = pdf_path
        except ImportError:
            console.print("[yellow]Warning: PDF export not available[/yellow]")

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

    This shows the full prompt that would be sent to DALL-E, without
    actually generating an image (no API key required).
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

    console.print("[dim]Enhanced prompt (sent to DALL-E):[/dim]")
    console.print(f"  [green]{enhanced}[/green]\n")

    console.print("[dim]Tip: Use this enhanced prompt with --style in the generate command[/dim]")


@app.command()
def generate(
    prompt: str = typer.Argument(
        ...,
        help="Description of image to generate"
    ),
    style: str = typer.Option(
        "simple",
        "--style", "-s",
        help="Style preset (simple, christmas, nature, pixel_art)"
    ),
    size: int = typer.Option(
        40,
        "--size",
        help="Grid size for pattern"
    ),
    colors: int = typer.Option(
        8,
        "--colors", "-c",
        help="Number of colors"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory"
    )
):
    """Generate a cross-stitch pattern from a text description using AI."""
    try:
        from .core.ai_generator import AIGenerator
        from .prompts.templates import get_template
    except ImportError as e:
        console.print(f"[red]Error: AI generation not available - {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold blue]XStitchLab[/bold blue] - AI Pattern Generation\n")
    console.print(f"  Prompt: {prompt}")
    console.print(f"  Style: {style}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating image with DALL-E...", total=None)

        generator = AIGenerator()
        enhanced_prompt = get_template(style, prompt)
        image_path = generator.generate(enhanced_prompt)

        progress.update(task, completed=True)

    console.print(f"[green]✓[/green] Image generated: {image_path}\n")

    # Now convert to pattern
    pattern, original, pixelated = create_pattern_from_image(
        image_path,
        grid_size=size,
        n_colors=colors,
        use_dithering=False,
        use_lab_colors=True,
        title=prompt[:30]
    )

    output_dir = output or Path.cwd()
    exporter = PNGExporter(output_dir)
    exports = exporter.export_all(pattern, "generated_pattern", original, pixelated)

    console.print("[green]✓[/green] Pattern created!\n")

    for name, path in exports.items():
        console.print(f"  • {name}: {path}")


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
    pattern_file: Path = typer.Argument(
        ...,
        help="Path to pattern JSON file",
        exists=True
    ),
    fabric_count: int = typer.Option(
        14,
        "--fabric", "-f",
        help="Aida fabric count (14, 16, or 18)"
    ),
    wastage: float = typer.Option(
        0.2,
        "--wastage", "-w",
        help="Thread wastage factor (0.1-0.3)"
    )
):
    """Estimate thread requirements for a pattern."""
    try:
        from .core.thread_calc import ThreadCalculator
    except ImportError:
        console.print("[red]Thread calculator not available[/red]")
        raise typer.Exit(1)

    pattern = Pattern.from_json(pattern_file)
    calc = ThreadCalculator(fabric_count=fabric_count, wastage_factor=wastage)

    estimates = calc.estimate_all(pattern)

    console.print(f"\n[bold]Thread Estimates for {pattern.metadata.title}[/bold]\n")
    console.print(f"Fabric: {fabric_count}-count Aida")
    console.print(f"Size: {pattern.metadata.width}×{pattern.metadata.height} stitches\n")

    table = Table(title="Shopping List")
    table.add_column("DMC Code", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Stitches")
    table.add_column("Meters")
    table.add_column("Skeins")

    total_skeins = 0
    for est in estimates:
        table.add_row(
            est["dmc_code"],
            est["name"],
            f"{est['stitch_count']:,}",
            f"{est['meters']:.1f}",
            str(est["skeins"])
        )
        total_skeins += est["skeins"]

    console.print(table)
    console.print(f"\n[bold]Total Skeins Needed: {total_skeins}[/bold]")


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
