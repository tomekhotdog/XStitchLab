"""PNG export functionality for cross-stitch patterns."""

from pathlib import Path
from PIL import Image
from typing import Optional

from ..core.pattern import Pattern
from ..core.visualizer import (
    render_color_preview,
    render_symbol_grid,
    render_thread_realistic,
    render_legend,
    create_pattern_sheet,
    render_comparison
)


class PNGExporter:
    """Export patterns to PNG images."""

    def __init__(self, output_dir: Optional[Path | str] = None):
        """Initialize exporter.

        Args:
            output_dir: Directory for output files (defaults to current dir)
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_path(self, base_name: str, suffix: str) -> Path:
        """Generate output path with given suffix."""
        return self.output_dir / f"{base_name}_{suffix}.png"

    def export_color_preview(
        self,
        pattern: Pattern,
        base_name: str = "pattern",
        cell_size: int = 10,
        show_grid: bool = True
    ) -> Path:
        """Export color preview image.

        Args:
            pattern: Pattern to export
            base_name: Base filename (without extension)
            cell_size: Size of each stitch cell in pixels
            show_grid: Whether to show grid lines

        Returns:
            Path to exported file
        """
        img = render_color_preview(pattern, cell_size, show_grid)
        path = self._get_output_path(base_name, "color_preview")
        img.save(path, "PNG")
        return path

    def export_symbol_grid(
        self,
        pattern: Pattern,
        base_name: str = "pattern",
        cell_size: int = 20,
        show_grid: bool = True
    ) -> Path:
        """Export symbol grid image for stitching.

        Args:
            pattern: Pattern to export
            base_name: Base filename
            cell_size: Size of each stitch cell in pixels
            show_grid: Whether to show grid lines

        Returns:
            Path to exported file
        """
        img = render_symbol_grid(pattern, cell_size, show_grid)
        path = self._get_output_path(base_name, "symbol_grid")
        img.save(path, "PNG")
        return path

    def export_realistic(
        self,
        pattern: Pattern,
        base_name: str = "pattern",
        cell_size: int = 8
    ) -> Path:
        """Export thread-realistic preview.

        Args:
            pattern: Pattern to export
            base_name: Base filename
            cell_size: Size of each stitch cell in pixels

        Returns:
            Path to exported file
        """
        img = render_thread_realistic(pattern, cell_size)
        path = self._get_output_path(base_name, "realistic")
        img.save(path, "PNG")
        return path

    def export_legend(
        self,
        pattern: Pattern,
        base_name: str = "pattern"
    ) -> Path:
        """Export color legend image.

        Args:
            pattern: Pattern to export
            base_name: Base filename

        Returns:
            Path to exported file
        """
        img = render_legend(pattern)
        path = self._get_output_path(base_name, "legend")
        img.save(path, "PNG")
        return path

    def export_pattern_sheet(
        self,
        pattern: Pattern,
        base_name: str = "pattern",
        show_grid_numbers: bool = True
    ) -> Path:
        """Export complete pattern sheet with grid and legend.

        Args:
            pattern: Pattern to export
            base_name: Base filename
            show_grid_numbers: Whether to show row/column numbers

        Returns:
            Path to exported file
        """
        img = create_pattern_sheet(pattern, show_grid_numbers)
        path = self._get_output_path(base_name, "sheet")
        img.save(path, "PNG")
        return path

    def export_comparison(
        self,
        original: Image.Image,
        pixelated: Image.Image,
        pattern: Pattern,
        base_name: str = "pattern"
    ) -> Path:
        """Export side-by-side comparison image.

        Args:
            original: Original input image
            pixelated: Pixelated version
            pattern: Final pattern
            base_name: Base filename

        Returns:
            Path to exported file
        """
        img = render_comparison(original, pixelated, pattern)
        path = self._get_output_path(base_name, "comparison")
        img.save(path, "PNG")
        return path

    def export_all(
        self,
        pattern: Pattern,
        base_name: str = "pattern",
        original: Optional[Image.Image] = None,
        pixelated: Optional[Image.Image] = None
    ) -> dict[str, Path]:
        """Export all PNG variants of the pattern.

        Args:
            pattern: Pattern to export
            base_name: Base filename
            original: Optional original image for comparison
            pixelated: Optional pixelated image for comparison

        Returns:
            Dictionary mapping export type to file path
        """
        exports = {}

        exports["color_preview"] = self.export_color_preview(pattern, base_name)
        exports["symbol_grid"] = self.export_symbol_grid(pattern, base_name)
        exports["realistic"] = self.export_realistic(pattern, base_name)
        exports["legend"] = self.export_legend(pattern, base_name)
        exports["sheet"] = self.export_pattern_sheet(pattern, base_name)

        if original and pixelated:
            exports["comparison"] = self.export_comparison(
                original, pixelated, pattern, base_name
            )

        return exports


def quick_export(
    pattern: Pattern,
    output_path: Path | str,
    mode: str = "sheet"
) -> Path:
    """Quick export of a pattern to a single PNG file.

    Args:
        pattern: Pattern to export
        output_path: Full path for output file
        mode: Export mode - "sheet", "color", "symbol", "realistic"

    Returns:
        Path to exported file
    """
    output_path = Path(output_path)

    if mode == "sheet":
        img = create_pattern_sheet(pattern)
    elif mode == "color":
        img = render_color_preview(pattern)
    elif mode == "symbol":
        img = render_symbol_grid(pattern)
    elif mode == "realistic":
        img = render_thread_realistic(pattern)
    else:
        raise ValueError(f"Unknown export mode: {mode}")

    img.save(output_path, "PNG")
    return output_path
