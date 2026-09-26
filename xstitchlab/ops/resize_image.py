"""Resize an image (image -> image); used before quantizing photos."""

from typing import Literal

from PIL import Image
from pydantic import Field

from xstitchlab.core import pixelator
from xstitchlab.ops._image import target_size
from xstitchlab.ops.base import OpParams

NAME = "resize_image"
KIND = "image"
GROUP = "import"
TITLE = "Resize image"
DESCRIPTION = "Resize to width x height pixels (height follows the aspect ratio when omitted)."


class Params(OpParams):
    width: int = Field(50, ge=4, le=400)
    height: int | None = Field(None, ge=1, le=400)
    method: Literal["lanczos", "nearest"] = "lanczos"


def apply(img: Image.Image, params: Params) -> Image.Image:
    width, height = target_size(img, params.width, params.height)
    return pixelator.resize_to_grid(
        img.convert("RGB"), width, height, maintain_aspect=False, resample_method=params.method
    )
