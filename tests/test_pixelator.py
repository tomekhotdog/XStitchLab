"""Tests for image pixelation and color quantization."""

import pytest
import numpy as np
from PIL import Image

from xstitchlab.core.pixelator import (
    resize_to_grid,
    quantize_colors_kmeans,
    quantize_colors_median_cut,
    pixelate,
    get_color_indices,
    merge_similar_colors,
)


class TestResizeToGrid:
    """Tests for resize_to_grid function."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        return Image.new("RGB", (100, 100), (255, 0, 0))

    def test_resize_square(self, sample_image):
        """Test resizing a square image."""
        resized = resize_to_grid(sample_image, 40)
        assert resized.width == 40
        assert resized.height == 40

    def test_resize_rectangular(self):
        """Test resizing a rectangular image."""
        img = Image.new("RGB", (200, 100), (0, 255, 0))
        resized = resize_to_grid(img, 40)
        assert resized.width == 40
        assert resized.height == 20  # Maintains 2:1 aspect ratio

    def test_resize_explicit_height(self, sample_image):
        """Test resizing with explicit height."""
        resized = resize_to_grid(sample_image, 40, 30, maintain_aspect=False)
        assert resized.width == 40
        assert resized.height == 30


class TestQuantizeColors:
    """Tests for color quantization functions."""

    @pytest.fixture
    def gradient_image(self):
        """Create an image with many colors (gradient)."""
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            for j in range(100):
                arr[i, j] = [i * 2, j * 2, 128]
        return Image.fromarray(arr)

    def test_kmeans_reduces_colors(self, gradient_image):
        """Test k-means reduces to target color count."""
        quantized, palette = quantize_colors_kmeans(gradient_image, n_colors=8)

        # Check palette size
        assert len(palette) == 8

        # Check image is same size
        assert quantized.size == gradient_image.size

        # Verify quantized image only uses palette colors
        unique = np.unique(np.array(quantized).reshape(-1, 3), axis=0)
        assert len(unique) <= 8

    def test_median_cut_reduces_colors(self, gradient_image):
        """Test median cut reduces to target color count."""
        quantized, palette = quantize_colors_median_cut(gradient_image, n_colors=8)

        assert len(palette) <= 8
        assert quantized.size == gradient_image.size

    def test_kmeans_reproducible(self, gradient_image):
        """Test k-means produces reproducible results with same seed."""
        q1, p1 = quantize_colors_kmeans(gradient_image, n_colors=5, random_state=42)
        q2, p2 = quantize_colors_kmeans(gradient_image, n_colors=5, random_state=42)

        np.testing.assert_array_equal(np.array(q1), np.array(q2))
        np.testing.assert_array_equal(p1, p2)


class TestPixelate:
    """Tests for the pixelate pipeline."""

    @pytest.fixture
    def photo_like_image(self):
        """Create an image with realistic color variation."""
        arr = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        return Image.fromarray(arr)

    def test_pixelate_basic(self, photo_like_image):
        """Test basic pixelation pipeline."""
        pixelated, palette = pixelate(
            photo_like_image,
            grid_width=40,
            n_colors=8
        )

        assert pixelated.width == 40
        assert len(palette) == 8

    def test_pixelate_with_dithering(self, photo_like_image):
        """Test pixelation with dithering enabled."""
        pixelated, palette = pixelate(
            photo_like_image,
            grid_width=40,
            n_colors=8,
            use_dithering=True
        )

        assert pixelated.width == 40
        # Dithered image may have more visible colors due to mixing
        assert len(palette) <= 8


class TestGetColorIndices:
    """Tests for get_color_indices function."""

    def test_indices_match_colors(self):
        """Test that indices correctly map to palette colors."""
        # Create simple image with known colors
        arr = np.array([
            [[255, 0, 0], [0, 255, 0]],
            [[0, 255, 0], [255, 0, 0]]
        ], dtype=np.uint8)
        img = Image.fromarray(arr)

        palette = np.array([[255, 0, 0], [0, 255, 0]], dtype=np.uint8)

        indices = get_color_indices(img, palette)

        assert indices[0, 0] == 0  # Red
        assert indices[0, 1] == 1  # Green
        assert indices[1, 0] == 1  # Green
        assert indices[1, 1] == 0  # Red


class TestMergeSimilarColors:
    """Tests for merge_similar_colors function."""

    def test_merge_identical_colors(self):
        """Test merging of very similar colors."""
        palette = np.array([
            [255, 0, 0],    # Red
            [255, 5, 0],    # Nearly identical red
            [0, 0, 255],    # Blue
        ], dtype=np.uint8)

        indices = np.array([
            [0, 1],
            [2, 0]
        ])

        new_palette, new_indices = merge_similar_colors(palette, indices, threshold=30)

        # Should merge the two reds
        assert len(new_palette) == 2

    def test_no_merge_different_colors(self):
        """Test that different colors aren't merged."""
        palette = np.array([
            [255, 0, 0],    # Red
            [0, 255, 0],    # Green
            [0, 0, 255],    # Blue
        ], dtype=np.uint8)

        indices = np.array([[0, 1, 2]])

        new_palette, new_indices = merge_similar_colors(palette, indices, threshold=30)

        # All colors should be preserved
        assert len(new_palette) == 3
