"""Reduce an image to a small palette before pixelating."""

from typing import Literal

import numpy as np
from PIL import Image
from pydantic import Field
from sklearn.cluster import MiniBatchKMeans

from xstitchlab.core import pixelator
from xstitchlab.ops.base import OpError, OpParams

NAME = "quantize_image"
KIND = "image"
GROUP = "import"
TITLE = "Quantize colours"
DESCRIPTION = (
    "Reduce the image to n_colors flat colours (k-means or median cut), or keep its "
    "exact palette (unique, for images that already have one). Optional dithering."
)

MAX_UNIQUE = 256


class Params(OpParams):
    method: Literal["kmeans", "median_cut", "unique"] = "kmeans"
    n_colors: int = Field(8, ge=2, le=64)
    dither: bool = False


def apply(img: Image.Image, params: Params) -> Image.Image:
    img = img.convert("RGB")
    if params.method == "unique":
        _, palette = pixelator.extract_unique_colors(img)
        if len(palette) > MAX_UNIQUE:
            raise OpError(
                f"image has {len(palette)} colours; 'unique' allows at most {MAX_UNIQUE} "
                "(quantize with kmeans or median_cut instead)"
            )
        return img
    if params.method == "kmeans":
        quantized, palette = _kmeans(img, params.n_colors)
    else:
        quantized, palette = pixelator.quantize_colors_median_cut(img, params.n_colors)
    if params.dither:
        return _dither_to_palette(img, palette)
    return quantized


def _kmeans(img: Image.Image, n_colors: int) -> tuple[Image.Image, np.ndarray]:
    """Fit on every pixel at full resolution; palette = cluster centres (the old backend path)."""
    arr = np.asarray(img)
    pixels = arr.reshape(-1, 3).astype(np.float32)
    n_clusters = min(n_colors, len(np.unique(pixels, axis=0)))
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init=1, batch_size=1024)
    labels = kmeans.fit_predict(pixels)
    palette = np.clip(np.rint(kmeans.cluster_centers_), 0, 255).astype(np.uint8)
    return Image.fromarray(palette[labels].reshape(arr.shape)), palette


def _dither_to_palette(img: Image.Image, palette: np.ndarray) -> Image.Image:
    """Floyd-Steinberg dither the source image onto the chosen palette."""
    palette_img = Image.new("P", (1, 1))
    entries = [tuple(int(v) for v in c) for c in palette]
    entries += [entries[-1]] * (256 - len(entries))   # pad with a real colour, never black
    palette_img.putpalette([v for c in entries for v in c])
    return img.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")
