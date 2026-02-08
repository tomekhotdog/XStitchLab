"""Tests for color mapping functionality."""

import pytest
import numpy as np

from xstitchlab.core.color_mapper import (
    ColorMapper,
    color_distance_rgb,
    color_distance_lab,
    find_nearest_dmc_rgb,
)
from xstitchlab.core.pattern import DMCPalette


class TestColorDistance:
    """Tests for color distance functions."""

    def test_rgb_distance_same_color(self):
        """Test RGB distance for identical colors."""
        dist = color_distance_rgb((255, 0, 0), (255, 0, 0))
        assert dist == 0

    def test_rgb_distance_black_white(self):
        """Test RGB distance between black and white."""
        dist = color_distance_rgb((0, 0, 0), (255, 255, 255))
        # sqrt(255^2 * 3) ≈ 441.67
        assert abs(dist - 441.67) < 1

    def test_rgb_distance_symmetry(self):
        """Test that RGB distance is symmetric."""
        c1 = (100, 50, 200)
        c2 = (150, 75, 100)
        assert color_distance_rgb(c1, c2) == color_distance_rgb(c2, c1)

    def test_lab_distance_same_color(self):
        """Test LAB distance for identical colors."""
        dist = color_distance_lab((128, 128, 128), (128, 128, 128))
        assert dist < 0.1  # Should be essentially 0

    def test_lab_distance_different_colors(self):
        """Test LAB distance for different colors."""
        dist = color_distance_lab((255, 0, 0), (0, 255, 0))
        assert dist > 50  # Very different colors


class TestColorMapper:
    """Tests for ColorMapper class."""

    @pytest.fixture
    def mapper_rgb(self):
        """Create mapper using RGB distance."""
        return ColorMapper(use_lab=False)

    @pytest.fixture
    def mapper_lab(self):
        """Create mapper using LAB distance."""
        return ColorMapper(use_lab=True)

    def test_find_nearest_black(self, mapper_rgb):
        """Test finding nearest DMC for pure black."""
        dmc = mapper_rgb.find_nearest((0, 0, 0))
        assert dmc.code == "310"  # DMC 310 is Black

    def test_find_nearest_white(self, mapper_rgb):
        """Test finding nearest DMC for pure white."""
        dmc = mapper_rgb.find_nearest((255, 255, 255))
        # Should be White or B5200 (Snow White)
        assert dmc.code in ["White", "B5200"]

    def test_find_nearest_red(self, mapper_lab):
        """Test finding nearest DMC for red."""
        dmc = mapper_lab.find_nearest((255, 0, 0))
        # Should be a red DMC color
        assert "red" in dmc.name.lower() or dmc.rgb[0] > 200

    def test_caching(self, mapper_rgb):
        """Test that results are cached."""
        color = (128, 64, 192)

        # First call
        result1 = mapper_rgb.find_nearest(color)

        # Check cache
        assert color in mapper_rgb._cache

        # Second call should return same object
        result2 = mapper_rgb.find_nearest(color)
        assert result1 is result2

    def test_clear_cache(self, mapper_rgb):
        """Test clearing cache."""
        mapper_rgb.find_nearest((100, 100, 100))
        assert len(mapper_rgb._cache) > 0

        mapper_rgb.clear_cache()
        assert len(mapper_rgb._cache) == 0

    def test_map_palette(self, mapper_rgb):
        """Test mapping multiple colors."""
        colors = np.array([
            [255, 255, 255],  # White
            [0, 0, 0],        # Black
            [255, 0, 0],      # Red
        ])

        dmc_colors = mapper_rgb.map_palette(colors)

        assert len(dmc_colors) == 3
        assert dmc_colors[0].code in ["White", "B5200"]
        assert dmc_colors[1].code == "310"

    def test_map_image(self, mapper_rgb):
        """Test mapping an image array."""
        # Create a simple 2x2 test image
        img = np.array([
            [[255, 255, 255], [0, 0, 0]],
            [[0, 0, 0], [255, 255, 255]]
        ], dtype=np.uint8)

        mapped, unique_colors = mapper_rgb.map_image(img)

        assert mapped.shape == img.shape
        assert len(unique_colors) == 2

    def test_get_substitutes(self, mapper_lab):
        """Test getting alternative colors."""
        palette = DMCPalette()
        red = palette.get_by_code("321")  # Christmas Red

        alternatives = mapper_lab.get_substitutes(red, n_alternatives=3)

        assert len(alternatives) == 3
        # All alternatives should be different from original
        for alt, dist in alternatives:
            assert alt.code != red.code
            assert dist > 0

    def test_reduce_to_max_colors(self, mapper_rgb):
        """Test reducing palette to max colors."""
        palette = DMCPalette()
        colors = list(palette.colors[:10])

        stitch_counts = {c.code: i * 100 for i, c in enumerate(colors)}

        reduced = mapper_rgb.reduce_to_max_colors(
            colors,
            max_colors=5,
            stitch_counts=stitch_counts
        )

        assert len(reduced) == 5
        # Should keep highest count colors
        reduced_codes = {c.code for c in reduced}
        assert colors[9].code in reduced_codes  # Highest count

    def test_reduce_no_change_needed(self, mapper_rgb):
        """Test reduce when already under limit."""
        palette = DMCPalette()
        colors = list(palette.colors[:3])

        reduced = mapper_rgb.reduce_to_max_colors(colors, max_colors=5)

        assert len(reduced) == 3
