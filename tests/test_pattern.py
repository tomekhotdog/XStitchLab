"""Tests for pattern data structures."""

import pytest
import json
import tempfile
from pathlib import Path

from xstitchlab.core.pattern import (
    DMCColor,
    ColorLegendEntry,
    PatternMetadata,
    Pattern,
    DMCPalette
)


class TestDMCColor:
    """Tests for DMCColor class."""

    def test_create_color(self):
        """Test basic color creation."""
        color = DMCColor(code="310", name="Black", rgb=(0, 0, 0))
        assert color.code == "310"
        assert color.name == "Black"
        assert color.rgb == (0, 0, 0)

    def test_to_hex(self):
        """Test hex conversion."""
        color = DMCColor(code="666", name="Christmas Red", rgb=(227, 29, 66))
        assert color.to_hex() == "#e31d42"

    def test_to_hex_white(self):
        """Test hex conversion for white."""
        color = DMCColor(code="White", name="White", rgb=(255, 255, 255))
        assert color.to_hex() == "#ffffff"

    def test_from_dict(self):
        """Test creating color from dictionary."""
        data = {"code": "321", "name": "Christmas Red", "rgb": [199, 43, 59]}
        color = DMCColor.from_dict(data)
        assert color.code == "321"
        assert color.rgb == (199, 43, 59)


class TestPatternMetadata:
    """Tests for PatternMetadata class."""

    def test_default_values(self):
        """Test default metadata values."""
        meta = PatternMetadata()
        assert meta.title == "Untitled Pattern"
        assert meta.fabric_count == 14

    def test_fabric_size_calculation(self):
        """Test fabric size calculations."""
        meta = PatternMetadata(width=40, height=60, fabric_count=14)
        # Width should be 40/14 + 2 = ~4.86 inches
        assert abs(meta.fabric_width_inches - 4.86) < 0.1
        # Height should be 60/14 + 2 = ~6.29 inches
        assert abs(meta.fabric_height_inches - 6.29) < 0.1

    def test_difficulty_rating_easy(self):
        """Test easy difficulty rating."""
        meta = PatternMetadata(color_count=4, total_stitches=1000)
        assert meta.get_difficulty_rating() == "easy"

    def test_difficulty_rating_medium(self):
        """Test medium difficulty rating."""
        meta = PatternMetadata(color_count=8, total_stitches=3000)
        assert meta.get_difficulty_rating() == "medium"

    def test_difficulty_rating_hard(self):
        """Test hard difficulty rating."""
        meta = PatternMetadata(color_count=15, total_stitches=10000)
        assert meta.get_difficulty_rating() == "hard"


class TestPattern:
    """Tests for Pattern class."""

    @pytest.fixture
    def simple_pattern(self):
        """Create a simple test pattern."""
        grid = [
            [0, 1, 0],
            [1, 0, 1],
            [0, 1, 0]
        ]
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor("White", "White", (255, 255, 255)),
                symbol="●",
                stitch_count=0
            ),
            ColorLegendEntry(
                dmc_color=DMCColor("310", "Black", (0, 0, 0)),
                symbol="■",
                stitch_count=0
            )
        ]
        return Pattern(grid=grid, legend=legend)

    def test_pattern_dimensions(self, simple_pattern):
        """Test pattern dimensions are calculated correctly."""
        assert simple_pattern.metadata.width == 3
        assert simple_pattern.metadata.height == 3

    def test_count_stitches(self, simple_pattern):
        """Test stitch counting."""
        counts = simple_pattern.count_stitches()
        assert counts["White"] == 5
        assert counts["310"] == 4

    def test_get_symbol(self, simple_pattern):
        """Test getting symbol for color index."""
        assert simple_pattern.get_symbol(0) == "●"
        assert simple_pattern.get_symbol(1) == "■"

    def test_get_color_at(self, simple_pattern):
        """Test getting color at position."""
        color = simple_pattern.get_color_at(0, 0)
        assert color.code == "White"

        color = simple_pattern.get_color_at(1, 0)
        assert color.code == "310"

    def test_to_dict(self, simple_pattern):
        """Test converting pattern to dictionary."""
        simple_pattern.count_stitches()
        data = simple_pattern.to_dict()

        assert "metadata" in data
        assert "legend" in data
        assert "grid" in data
        assert data["metadata"]["width"] == 3
        assert len(data["legend"]) == 2

    def test_json_roundtrip(self, simple_pattern):
        """Test saving and loading pattern as JSON."""
        simple_pattern.count_stitches()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            simple_pattern.to_json(path)
            loaded = Pattern.from_json(path)

            assert loaded.metadata.width == simple_pattern.metadata.width
            assert len(loaded.legend) == len(simple_pattern.legend)
            assert loaded.grid == simple_pattern.grid
        finally:
            path.unlink()


class TestDMCPalette:
    """Tests for DMCPalette class."""

    def test_load_palette(self):
        """Test loading DMC palette."""
        palette = DMCPalette()
        assert len(palette) > 400  # Should have ~500 colors

    def test_get_by_code(self):
        """Test finding color by code."""
        palette = DMCPalette()
        color = palette.get_by_code("310")
        assert color is not None
        assert color.name == "Black"

    def test_get_by_code_not_found(self):
        """Test finding non-existent code."""
        palette = DMCPalette()
        color = palette.get_by_code("INVALID")
        assert color is None

    def test_get_all_rgb(self):
        """Test getting all RGB values."""
        palette = DMCPalette()
        rgbs = palette.get_all_rgb()
        assert len(rgbs) == len(palette)
        assert all(len(rgb) == 3 for rgb in rgbs)

    def test_iteration(self):
        """Test iterating over palette."""
        palette = DMCPalette()
        colors = list(palette)
        assert len(colors) == len(palette)
        assert all(isinstance(c, DMCColor) for c in colors)
