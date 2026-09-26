"""Discover ops in `xstitchlab.ops`, validate recipes, and run them.

Recipe shape: zero or more `image` ops, exactly one `pixelate` op, zero or more
`pattern` ops. `run_pattern_ops`/`apply_one` accept only the pattern tail.
"""

import importlib
import pkgutil

from PIL import Image
from pydantic import ValidationError

from xstitchlab.core.pattern import OpCall, Pattern
from xstitchlab.ops.base import OpError, RunResult, Step

_REQUIRED_ATTRS = ("NAME", "KIND", "GROUP", "TITLE", "DESCRIPTION", "Params", "apply")
_SKIP_MODULES = {"base", "registry"}

_ops: dict[str, object] | None = None


# --- registry ----------------------------------------------------------------

def register(op) -> None:
    """Register any object exposing the `Operation` attributes, keyed by `NAME`."""
    _ensure_discovered()
    _ops[op.NAME] = op


def reset() -> None:
    """Forget every registered op and re-discover the package."""
    global _ops
    _ops = None
    _ensure_discovered()


def get(name: str):
    _ensure_discovered()
    try:
        return _ops[name]
    except KeyError:
        raise OpError(f"unknown op: {name}") from None


def schemas() -> list[dict]:
    """Op descriptors for the UI, sorted by group then name."""
    _ensure_discovered()
    entries = [
        {
            "name": op.NAME,
            "kind": op.KIND,
            "group": op.GROUP,
            "title": op.TITLE,
            "description": op.DESCRIPTION,
            "schema": op.Params.model_json_schema(),
        }
        for op in _ops.values()
    ]
    return sorted(entries, key=lambda e: (e["group"], e["name"]))


def _ensure_discovered() -> None:
    global _ops
    if _ops is not None:
        return
    _ops = {}
    import xstitchlab.ops as package
    for info in pkgutil.iter_modules(package.__path__):
        if info.name in _SKIP_MODULES or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package.__name__}.{info.name}")
        if all(hasattr(module, attr) for attr in _REQUIRED_ATTRS):
            register(module)


# --- validation --------------------------------------------------------------

def validate_recipe(recipe: list[OpCall], *, require_pixelate: bool = True) -> None:
    """Check names, params, and stage order. Raises `OpError` with `step_index`."""
    seen_pixelate = not require_pixelate
    for i, call in enumerate(recipe):
        op = _get_at(call.op, i)
        _params_at(op, call, i)
        if op.KIND == "pattern" and not seen_pixelate:
            raise OpError(f"{call.op}: pattern op before the pixelate op", i, call.op)
        if op.KIND != "pattern" and seen_pixelate:
            if not require_pixelate:
                what = "only pattern ops allowed after pixelate"
            elif op.KIND == "pixelate":
                what = "recipe already has a pixelate op"
            else:
                what = "image op after the pixelate op"
            raise OpError(f"{call.op}: {what}", i, call.op)
        seen_pixelate = seen_pixelate or op.KIND == "pixelate"
    if require_pixelate and not seen_pixelate:
        raise OpError("recipe has no pixelate op")


def _get_at(name: str, i: int):
    try:
        return get(name)
    except OpError as e:
        e.step_index, e.op = i, name
        raise


def _params_at(op, call: OpCall, i: int):
    try:
        return op.Params(**call.params)
    except ValidationError as e:
        raise OpError(f"{call.op}: invalid params: {e}", i, call.op) from e


# --- execution ---------------------------------------------------------------

def run_recipe(image: Image.Image, recipe: list[OpCall]) -> RunResult:
    """Fold a full recipe over an image; the pixelate op turns it into a Pattern."""
    validate_recipe(recipe)
    subject, steps = image, []
    for i, call in enumerate(recipe):
        subject = _run_step(subject, call, i, steps)
    subject.recipe = list(recipe)
    return RunResult(pattern=subject, steps=steps)


def run_pattern_ops(pattern: Pattern, ops: list[OpCall]) -> RunResult:
    """Fold pattern ops over a copy of `pattern`, extending its recipe."""
    validate_recipe(ops, require_pixelate=False)
    subject, steps = pattern.copy(), []
    for i, call in enumerate(ops):
        subject = _run_step(subject, call, i, steps)
    subject.recipe = list(pattern.recipe) + list(ops)
    return RunResult(pattern=subject, steps=steps)


def apply_one(pattern: Pattern, call: OpCall) -> Pattern:
    return run_pattern_ops(pattern, [call]).pattern


def _run_step(subject, call: OpCall, i: int, steps: list[Step]):
    op = _get_at(call.op, i)
    params = _params_at(op, call, i)
    if isinstance(subject, Pattern):
        subject = subject.copy()
    try:
        result = op.apply(subject, params)
    except OpError as e:
        if e.step_index is None:
            e.step_index = i
        if e.op is None:
            e.op = call.op
        raise
    except Exception as e:
        raise OpError(f"{call.op} failed: {e}", i, call.op) from e
    steps.append(Step(name=call.op, params=dict(call.params), result=result, stats=_stats(result)))
    return result


def _stats(result) -> dict:
    if isinstance(result, Pattern):
        result.count_stitches()
        return {
            "width": result.width,
            "height": result.height,
            "colors": len(result.legend),
            "stitches": result.metadata.total_stitches,
            "backstitch": len(result.backstitch),
        }
    return {"width": result.width, "height": result.height}
