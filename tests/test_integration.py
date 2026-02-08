"""Integration tests for the complete XStitchLab pipeline."""

import pytest
from PIL import Image
import numpy as np
from pathlib import Path

from xstitchlab.core.image_input import load_image, load_image_as_array
from xstitchlab.core.pixelator import pixelate, get_color_indices
from xstitchlab.core.color_mapper import ColorMapper
from xstitchlab.core.pattern import Pattern, PatternMetadata, ColorLegendEntry
from xstitchlab.core.visualizer import (
    render_color_preview,
    render_symbol_grid,
    render_legend,
)
from xstitchlab.core.thread_calc import ThreadCalculator
from xstitchlab.export.png_exporter import PNGExporter


class TestFullPipeline:
    """Test the complete image-to-pattern pipeline."""

    # Standard symbols for patterns
    SYMBOLS = [
        "●", "■", "▲", "◆", "★", "♦", "♣", "♠", "♥", "○",
        "□", "△", "◇", "☆", "◐", "◑", "◒", "◓", "⬟", "⬡",
    ]

    def test_end_to_end_pipeline(self, sample_rgb_image, temp_dir):
        """Test complete pipeline from image to pattern."""
        # Step 1: Pixelate
        pixelated, palette = pixelate(
            sample_rgb_image,
            grid_width=20,
            n_colors=4
        )

        assert pixelated.width == 20
        assert len(palette) == 4

        # Step 2: Map to DMC
        mapper = ColorMapper(use_lab=False)  # RGB for speed
        dmc_colors = mapper.map_palette(palette)

        assert len(dmc_colors) == 4

        # Step 3: Get color indices
        indices = get_color_indices(pixelated, palette)

        assert indices.shape == (20, 20)

        # Step 4: Create pattern
        legend = [
            ColorLegendEntry(
                dmc_color=dmc,
                symbol=self.SYMBOLS[i],
                stitch_count=0
            )
            for i, dmc in enumerate(dmc_colors)
        ]

        pattern = Pattern(
            grid=indices.tolist(),
            legend=legend,
            metadata=PatternMetadata(title="Integration Test")
        )
        pattern.count_stitches()

        # Verify pattern
        assert pattern.metadata.width == 20
        assert pattern.metadata.height == 20
        assert pattern.metadata.color_count == 4
        assert pattern.metadata.total_stitches == 400

        # Step 5: Render visualizations
        color_preview = render_color_preview(pattern)
        symbol_grid = render_symbol_grid(pattern)
        legend_img = render_legend(pattern)

        assert color_preview.width > 0
        assert symbol_grid.width > 0
        assert legend_img.width > 0

        # Step 6: Export PNG
        exporter = PNGExporter(temp_dir)
        exports = exporter.export_all(pattern, "test_pattern", sample_rgb_image, pixelated)

        assert "color_preview" in exports
        assert exports["color_preview"].exists()

        # Step 7: Thread estimation
        calc = ThreadCalculator(fabric_count=14)
        estimates = calc.estimate_pattern(pattern)

        assert len(estimates) == 4
        total_skeins = sum(e.skeins_needed for e in estimates)
        assert total_skeins >= 1

    def test_pipeline_with_many_colors(self, gradient_image, temp_dir):
        """Test pipeline handles many colors correctly."""
        # Use gradient image which has many colors
        pixelated, palette = pixelate(
            gradient_image,
            grid_width=30,
            n_colors=12
        )

        mapper = ColorMapper(use_lab=True)
        dmc_colors = mapper.map_palette(palette)

        # Should reduce to 12 colors
        assert len(dmc_colors) == 12

        indices = get_color_indices(pixelated, palette)

        legend = [
            ColorLegendEntry(
                dmc_color=dmc,
                symbol=self.SYMBOLS[i],
                stitch_count=0
            )
            for i, dmc in enumerate(dmc_colors)
        ]

        pattern = Pattern(
            grid=indices.tolist(),
            legend=legend
        )
        pattern.count_stitches()

        assert pattern.metadata.color_count == 12

    def test_json_roundtrip(self, sample_rgb_image, temp_dir):
        """Test pattern can be saved to JSON and loaded back."""
        # Create pattern
        pixelated, palette = pixelate(sample_rgb_image, 15, 3)
        mapper = ColorMapper(use_lab=False)
        dmc_colors = mapper.map_palette(palette)
        indices = get_color_indices(pixelated, palette)

        legend = [
            ColorLegendEntry(dmc_color=dmc, symbol=self.SYMBOLS[i], stitch_count=0)
            for i, dmc in enumerate(dmc_colors)
        ]

        original = Pattern(
            grid=indices.tolist(),
            legend=legend,
            metadata=PatternMetadata(title="JSON Test")
        )
        original.count_stitches()

        # Save and load
        json_path = temp_dir / "pattern.json"
        original.to_json(json_path)
        loaded = Pattern.from_json(json_path)

        # Compare
        assert loaded.metadata.title == original.metadata.title
        assert loaded.metadata.width == original.metadata.width
        assert loaded.metadata.height == original.metadata.height
        assert loaded.metadata.color_count == original.metadata.color_count
        assert loaded.grid == original.grid

        for orig_entry, loaded_entry in zip(original.legend, loaded.legend):
            assert orig_entry.dmc_color.code == loaded_entry.dmc_color.code
            assert orig_entry.symbol == loaded_entry.symbol
            assert orig_entry.stitch_count == loaded_entry.stitch_count


class TestImageInput:
    """Test image input functionality."""

    def test_load_png(self, saved_test_image):
        """Test loading PNG image."""
        img = load_image(saved_test_image)
        assert img.mode == "RGB"
        assert img.size == (50, 50)

    def test_load_as_array(self, saved_test_image):
        """Test loading image as numpy array."""
        arr = load_image_as_array(saved_test_image)
        assert arr.shape == (50, 50, 3)
        assert arr.dtype == np.uint8


class TestVisualization:
    """Test visualization outputs."""

    @pytest.fixture
    def test_pattern(self):
        """Create a test pattern for visualization tests."""
        from xstitchlab.core.pattern import DMCColor

        grid = [
            [0, 1, 0, 1],
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [1, 0, 1, 0]
        ]
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor("White", "White", (255, 255, 255)),
                symbol="○",
                stitch_count=8
            ),
            ColorLegendEntry(
                dmc_color=DMCColor("310", "Black", (0, 0, 0)),
                symbol="●",
                stitch_count=8
            ),
        ]
        return Pattern(grid=grid, legend=legend)

    def test_color_preview_dimensions(self, test_pattern):
        """Test color preview has correct dimensions."""
        preview = render_color_preview(test_pattern, cell_size=10)
        assert preview.width == 4 * 10
        assert preview.height == 4 * 10

    def test_symbol_grid_dimensions(self, test_pattern):
        """Test symbol grid has correct dimensions."""
        grid = render_symbol_grid(test_pattern, cell_size=20)
        assert grid.width == 4 * 20
        assert grid.height == 4 * 20

    def test_legend_contains_all_colors(self, test_pattern):
        """Test legend image is created successfully."""
        legend = render_legend(test_pattern)
        assert legend.width > 0
        assert legend.height > 0
