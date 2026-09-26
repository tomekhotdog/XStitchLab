"""Import ops: quantize_image, resize_image, pixelate, and the default recipes."""

import copy

import numpy as np
import pytest
from PIL import Image

from xstitchlab.core.pattern import DMCPalette, OpCall, Pattern
from xstitchlab.ops import defaults, pixelate, quantize_image, registry, resize_image
from xstitchlab.ops.base import OpError


def four_block_image(size: int = 40) -> Image.Image:
    """Flat quadrants: red, green, blue, yellow (all map to distinct DMC codes)."""
    half = size // 2
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    arr[:half, :half] = [255, 0, 0]
    arr[:half, half:] = [0, 255, 0]
    arr[half:, :half] = [0, 0, 255]
    arr[half:, half:] = [255, 255, 0]
    return Image.fromarray(arr)


def unique_colors(img: Image.Image) -> int:
    return len(np.unique(np.array(img.convert("RGB")).reshape(-1, 3), axis=0))


# --- quantize_image ----------------------------------------------------------

@pytest.mark.parametrize("method", ["kmeans", "median_cut", "unique"])
def test_quantize_four_blocks_keeps_at_most_four_colours(method):
    out = quantize_image.apply(four_block_image(), quantize_image.Params(method=method, n_colors=4))
    assert out.mode == "RGB"
    assert unique_colors(out) <= 4


def test_quantize_kmeans_reduces_a_noisy_image_to_n_colors():
    rng = np.random.default_rng(0)
    img = Image.fromarray(rng.integers(0, 256, (40, 40, 3), dtype=np.uint8))
    out = quantize_image.apply(img, quantize_image.Params(method="kmeans", n_colors=5))
    assert unique_colors(out) <= 5


def test_quantize_dither_still_respects_n_colors():
    rng = np.random.default_rng(1)
    img = Image.fromarray(rng.integers(0, 256, (40, 40, 3), dtype=np.uint8))
    out = quantize_image.apply(img, quantize_image.Params(method="kmeans", n_colors=6, dither=True))
    assert unique_colors(out) <= 6


def test_quantize_unique_rejects_more_than_256_colours():
    i = np.arange(20 * 20)
    arr = np.stack([i // 256, i % 256, np.zeros_like(i)], axis=1).reshape(20, 20, 3)
    img = Image.fromarray(arr.astype(np.uint8))
    assert unique_colors(img) == 400
    with pytest.raises(OpError, match="256"):
        quantize_image.apply(img, quantize_image.Params(method="unique"))


def test_quantize_converts_rgba_input_to_rgb():
    img = four_block_image().convert("RGBA")
    out = quantize_image.apply(img, quantize_image.Params(method="unique"))
    assert out.mode == "RGB"


# --- resize_image ------------------------------------------------------------

def test_resize_preserves_aspect_when_height_is_none():
    img = Image.new("RGB", (200, 100), (10, 20, 30))
    out = resize_image.apply(img, resize_image.Params(width=20))
    assert out.size == (20, 10)


def test_resize_honours_explicit_height():
    img = Image.new("RGB", (200, 100), (10, 20, 30))
    out = resize_image.apply(img, resize_image.Params(width=20, height=20, method="nearest"))
    assert out.size == (20, 20)


# --- pixelate ----------------------------------------------------------------

def test_pixelate_majority_four_blocks_gives_four_uniform_quadrants():
    # steps=1: 100 -> 10 is one exact 10x10 block per cell, so quadrants stay crisp.
    pattern = pixelate.apply(four_block_image(100), pixelate.Params(width=10, sample="majority", steps=1))
    assert isinstance(pattern, Pattern)
    assert (pattern.width, pattern.height) == (10, 10)
    assert len({e.dmc_color.code for e in pattern.legend}) == 4
    grid = np.array(pattern.grid)
    quadrants = [grid[:5, :5], grid[:5, 5:], grid[5:, :5], grid[5:, 5:]]
    for q in quadrants:
        assert len(np.unique(q)) == 1
    assert len({int(q[0, 0]) for q in quadrants}) == 4


def test_pixelate_majority_multi_step_keeps_size_and_palette():
    # steps=3 goes 100 -> 46 -> 21 -> 10. boundary_preserving_resize pads every
    # intermediate to whole blocks with the edge colour, which shrinks the content
    # inside the frame (the legacy pipeline the finals were made with), so only the
    # size and the palette are stable enough to assert here.
    pattern = pixelate.apply(four_block_image(100), pixelate.Params(width=10, sample="majority", steps=3))
    assert (pattern.width, pattern.height) == (10, 10)
    assert len({e.dmc_color.code for e in pattern.legend}) == 4


def test_pixelate_nearest_sample_also_works():
    pattern = pixelate.apply(four_block_image(100), pixelate.Params(width=10, sample="nearest"))
    assert (pattern.width, pattern.height) == (10, 10)
    assert len(pattern.legend) == 4


def test_pixelate_height_none_preserves_aspect():
    img = Image.new("RGB", (200, 100), (200, 30, 30))
    pattern = pixelate.apply(img, pixelate.Params(width=20))
    assert (pattern.width, pattern.height) == (20, 10)


def test_pixelate_does_not_upscale_a_small_image():
    pattern = pixelate.apply(four_block_image(8), pixelate.Params(width=50))
    assert (pattern.width, pattern.height) == (8, 8)


def test_pixelate_merges_palette_colours_that_map_to_the_same_dmc():
    arr = np.zeros((10, 10, 3), dtype=np.uint8)
    arr[:, :5] = [128, 128, 128]
    arr[:, 5:] = [129, 129, 129]     # near-identical grey -> same DMC code
    pattern = pixelate.apply(Image.fromarray(arr), pixelate.Params(width=10))
    assert len(pattern.legend) == 1
    assert set(np.unique(np.array(pattern.grid)).tolist()) == {0}


def test_pixelate_legend_rgb_is_the_dmc_rgb_and_background_is_set():
    pattern = pixelate.apply(four_block_image(100), pixelate.Params(width=10, fabric_count=16))
    palette = DMCPalette()
    for entry in pattern.legend:
        assert entry.dmc_color.rgb == palette.get_by_code(entry.dmc_color.code).rgb
        assert entry.symbol
    assert pattern.background_index is not None
    assert pattern.metadata.fabric_count == 16
    assert pattern.metadata.total_stitches > 0


def test_pixelate_indices_are_compact_and_within_legend():
    pattern = pixelate.apply(four_block_image(100), pixelate.Params(width=10))
    used = set(np.unique(np.array(pattern.grid)).tolist())
    assert used == set(range(len(pattern.legend)))


# --- defaults ----------------------------------------------------------------

@pytest.mark.parametrize("name", list(defaults.DEFAULTS))
def test_default_recipes_validate(name):
    registry.validate_recipe(defaults.DEFAULTS[name])


def test_default_recipe_overrides_without_mutating_defaults():
    before = copy.deepcopy(defaults.DEFAULTS)
    recipe = defaults.default_recipe("photo", width=30, n_colors=5)
    assert [c.op for c in recipe] == ["resize_image", "quantize_image", "pixelate"]
    assert recipe[0].params["width"] == 30
    assert recipe[1].params["n_colors"] == 5
    assert recipe[2].params["width"] == 30
    assert defaults.DEFAULTS == before
    registry.validate_recipe(recipe)


def test_default_recipe_unknown_name_raises():
    with pytest.raises(OpError, match="unknown"):
        defaults.default_recipe("nope")


def test_run_recipe_end_to_end_with_predesigned_default():
    result = registry.run_recipe(four_block_image(100), defaults.default_recipe("predesigned", width=10, n_colors=4))
    assert (result.pattern.width, result.pattern.height) == (10, 10)
    assert [s.name for s in result.steps] == ["quantize_image", "pixelate"]
    assert result.pattern.recipe == [OpCall("quantize_image", {"method": "kmeans", "n_colors": 4}),
                                     OpCall("pixelate", {"width": 10, "sample": "majority", "steps": 3})]
