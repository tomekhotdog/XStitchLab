"""Pytest configuration and fixtures for XStitchLab tests."""

import pytest
import numpy as np
from PIL import Image
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_rgb_image():
    """Create a simple RGB test image."""
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    # Create some color regions
    arr[:50, :50] = [255, 0, 0]      # Red top-left
    arr[:50, 50:] = [0, 255, 0]      # Green top-right
    arr[50:, :50] = [0, 0, 255]      # Blue bottom-left
    arr[50:, 50:] = [255, 255, 0]    # Yellow bottom-right
    return Image.fromarray(arr)


@pytest.fixture
def gradient_image():
    """Create an image with smooth color gradients."""
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        for j in range(100):
            arr[i, j] = [
                int(255 * i / 100),
                int(255 * j / 100),
                128
            ]
    return Image.fromarray(arr)


@pytest.fixture
def saved_test_image(temp_dir):
    """Create and save a test image, returning its path."""
    img = Image.new("RGB", (50, 50), (128, 64, 192))
    path = temp_dir / "test_image.png"
    img.save(path)
    return path


@pytest.fixture
def dmc_palette():
    """Load DMC palette for testing."""
    from xstitchlab.core.pattern import DMCPalette
    return DMCPalette()
