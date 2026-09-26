"""Default recipes (replace the old "Mode" dropdown) and param overrides."""

import copy

from xstitchlab.core.pattern import OpCall
from xstitchlab.ops import registry
from xstitchlab.ops.base import OpError

PREDESIGNED = [
    OpCall("quantize_image", {"method": "kmeans", "n_colors": 8}),
    # steps=1: multi_step_resize pads each intermediate up to whole blocks, so several
    # steps shrink the content inside the frame (Riga: 90.6% match at 1 step vs 58.6% at 3).
    OpCall("pixelate", {"width": 50, "sample": "majority", "steps": 1}),
]
PHOTO = [
    OpCall("resize_image", {"width": 50, "method": "lanczos"}),
    OpCall("quantize_image", {"method": "kmeans", "n_colors": 8}),
    OpCall("pixelate", {"width": 50, "sample": "nearest"}),
]
DEFAULTS = {"predesigned": PREDESIGNED, "photo": PHOTO}


def default_recipe(name: str, *, width: int | None = None, n_colors: int | None = None) -> list[OpCall]:
    """Deep copy of a default with the width/n_colors params overridden where they occur."""
    try:
        recipe = DEFAULTS[name]
    except KeyError:
        raise OpError(f"unknown default recipe: {name!r} (choose from {sorted(DEFAULTS)})") from None
    return with_overrides(recipe, width=width, n_colors=n_colors)


def with_overrides(recipe: list[OpCall], *, width: int | None = None, n_colors: int | None = None) -> list[OpCall]:
    """Deep copy of `recipe`; each given value is set on every op whose Params accept it."""
    overrides = {k: v for k, v in {"width": width, "n_colors": n_colors}.items() if v is not None}
    copied = copy.deepcopy(recipe)
    for call in copied:
        fields = registry.get(call.op).Params.model_fields
        call.params.update({k: v for k, v in overrides.items() if k in fields})
    return copied
