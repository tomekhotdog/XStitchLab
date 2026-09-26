import types

import pytest
from PIL import Image
from pydantic import BaseModel, ValidationError

from tests.ops.helpers import small_pattern
from xstitchlab.core.pattern import OpCall, Pattern
from xstitchlab.ops import noop, registry
from xstitchlab.ops.base import OpError


@pytest.fixture(autouse=True)
def fresh_registry():
    registry.reset()
    yield
    registry.reset()


def fake_op(name, kind, apply, params_cls=None):
    if params_cls is None:
        class Params(BaseModel):
            pass
        params_cls = Params
    return types.SimpleNamespace(
        NAME=name, KIND=kind, GROUP="test", TITLE=name, DESCRIPTION="fake",
        Params=params_cls, apply=staticmethod(apply),
    )


# --- discovery / schemas ---------------------------------------------------

def test_registry_lists_ops_with_schema():
    ops = registry.schemas()
    names = {o["name"] for o in ops}
    assert "noop" in names
    noop_entry = next(o for o in ops if o["name"] == "noop")
    assert noop_entry["kind"] == "pattern" and noop_entry["group"] and noop_entry["title"]
    assert noop_entry["schema"]["type"] == "object"


def test_get_unknown_raises_op_error():
    with pytest.raises(OpError, match="unknown"):
        registry.get("does_not_exist")


def test_reset_drops_registered_fakes():
    registry.register(fake_op("ephemeral", "pattern", lambda p, _: p))
    assert registry.get("ephemeral").NAME == "ephemeral"
    registry.reset()
    with pytest.raises(OpError, match="unknown"):
        registry.get("ephemeral")


# --- validation --------------------------------------------------------------

def test_validate_recipe_requires_one_pixelate_after_image_ops():
    with pytest.raises(OpError, match="pixelate"):
        registry.validate_recipe([OpCall("noop")])            # pattern op with no pixelate
    with pytest.raises(OpError, match="unknown"):
        registry.validate_recipe([OpCall("does_not_exist")])


def test_validate_recipe_rejects_pattern_op_before_pixelate():
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    with pytest.raises(OpError, match="pixelate") as exc:
        registry.validate_recipe([OpCall("noop"), OpCall("fake_pixelate")])
    assert exc.value.step_index == 0
    assert exc.value.op == "noop"


def test_validate_recipe_rejects_two_pixelate_ops():
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    with pytest.raises(OpError, match="pixelate") as exc:
        registry.validate_recipe([OpCall("fake_pixelate"), OpCall("noop"), OpCall("fake_pixelate")])
    assert exc.value.step_index == 2
    assert exc.value.op == "fake_pixelate"


def test_validate_recipe_without_pixelate_allows_only_pattern_ops():
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    registry.validate_recipe([OpCall("noop"), OpCall("noop")], require_pixelate=False)
    with pytest.raises(OpError, match="pixelate") as exc:
        registry.validate_recipe([OpCall("fake_pixelate")], require_pixelate=False)
    assert exc.value.step_index == 0


def test_validate_params_uses_pydantic():
    with pytest.raises(ValidationError):
        registry.get("noop").Params(times="three")


def test_validate_recipe_wraps_param_errors_as_op_error():
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    with pytest.raises(OpError, match="times") as exc:
        registry.validate_recipe([OpCall("fake_pixelate"), OpCall("noop", {"times": "three"})])
    assert exc.value.step_index == 1
    assert exc.value.op == "noop"


# --- run_pattern_ops / apply_one -------------------------------------------

def test_run_recipe_on_pattern_skips_image_stage():
    p = small_pattern()
    result = registry.run_pattern_ops(p, [OpCall("noop", {"times": 2})])
    assert result.pattern.grid == p.grid
    assert [s.name for s in result.steps] == ["noop"]
    assert result.pattern.recipe == [OpCall("noop", {"times": 2})]


def test_run_pattern_ops_appends_to_existing_recipe():
    p = small_pattern()
    p.recipe = [OpCall("earlier")]
    result = registry.run_pattern_ops(p, [OpCall("noop")])
    assert result.pattern.recipe == [OpCall("earlier"), OpCall("noop")]
    assert p.recipe == [OpCall("earlier")]


def test_run_pattern_ops_passes_validated_params_to_apply(monkeypatch):
    seen = {}

    def spy(pattern, params):
        seen["params"] = params
        return pattern

    monkeypatch.setattr(noop, "apply", spy)
    registry.run_pattern_ops(small_pattern(), [OpCall("noop", {"times": 3})])
    assert isinstance(seen["params"], noop.Params)
    assert seen["params"].times == 3


def test_run_pattern_ops_param_failure_is_op_error():
    with pytest.raises(OpError, match="times") as exc:
        registry.run_pattern_ops(small_pattern(), [OpCall("noop"), OpCall("noop", {"times": "three"})])
    assert exc.value.step_index == 1
    assert exc.value.op == "noop"


def test_run_pattern_ops_wraps_exception_from_op(monkeypatch):
    def boom(pattern, params):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(noop, "apply", boom)
    with pytest.raises(OpError, match="noop failed: kaboom") as exc:
        registry.run_pattern_ops(small_pattern(), [OpCall("noop"), OpCall("noop")])
    assert exc.value.step_index == 0
    assert exc.value.op == "noop"


def test_run_pattern_ops_does_not_double_wrap_op_error(monkeypatch):
    def boom(pattern, params):
        raise OpError("custom message")

    monkeypatch.setattr(noop, "apply", boom)
    with pytest.raises(OpError) as exc:
        registry.run_pattern_ops(small_pattern(), [OpCall("noop"), OpCall("noop")])
    assert str(exc.value) == "custom message"
    assert exc.value.step_index == 0
    assert exc.value.op == "noop"


def test_run_pattern_ops_does_not_mutate_input(monkeypatch):
    def mutate(pattern, params):
        pattern.grid[2][2] = 1
        return pattern

    monkeypatch.setattr(noop, "apply", mutate)
    original = small_pattern()
    result = registry.run_pattern_ops(original, [OpCall("noop")])
    assert original.grid[2][2] == 2
    assert result.pattern.grid[2][2] == 1


def test_run_pattern_ops_refreshes_stats_after_mutation(monkeypatch):
    def mutate(pattern, params):
        pattern.grid[2][2] = 0   # centre becomes background: 9 -> 8 stitches
        return pattern

    monkeypatch.setattr(noop, "apply", mutate)
    result = registry.run_pattern_ops(small_pattern(), [OpCall("noop")])
    assert result.steps[0].stats == {
        "width": 5, "height": 5, "colors": 3, "stitches": 8, "backstitch": 0,
    }
    assert result.pattern.metadata.total_stitches == 8


def test_apply_one_returns_pattern_with_call_appended():
    p = small_pattern()
    out = registry.apply_one(p, OpCall("noop", {"times": 5}))
    assert isinstance(out, Pattern)
    assert out.recipe == [OpCall("noop", {"times": 5})]
    assert out.grid == p.grid
    assert p.recipe == []


# --- run_recipe (image stage) ----------------------------------------------

def test_run_recipe_end_to_end_with_image():
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    recipe = [OpCall("fake_pixelate"), OpCall("noop")]
    result = registry.run_recipe(Image.new("RGB", (10, 10)), recipe)
    assert [s.name for s in result.steps] == ["fake_pixelate", "noop"]
    assert result.steps[0].stats == {
        "width": 5, "height": 5, "colors": 3, "stitches": 9, "backstitch": 0,
    }
    assert isinstance(result.steps[0].result, Pattern)
    assert result.pattern.recipe == recipe
    assert result.pattern.grid == small_pattern().grid


def test_run_recipe_image_op_step_has_image_stats():
    registry.register(fake_op("fake_resize", "image", lambda img, _: img.resize((4, 3))))
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    result = registry.run_recipe(
        Image.new("RGB", (10, 10)), [OpCall("fake_resize"), OpCall("fake_pixelate")]
    )
    assert result.steps[0].stats == {"width": 4, "height": 3}
    assert isinstance(result.steps[0].result, Image.Image)
    assert result.steps[1].stats["width"] == 5


def test_run_recipe_rejects_recipe_without_pixelate():
    registry.register(fake_op("fake_resize", "image", lambda img, _: img))
    with pytest.raises(OpError, match="pixelate"):
        registry.run_recipe(Image.new("RGB", (10, 10)), [OpCall("fake_resize")])


def test_run_recipe_wraps_exception_with_step_index():
    def boom(img, _):
        raise ValueError("bad image")

    registry.register(fake_op("fake_resize", "image", lambda img, _: img))
    registry.register(fake_op("fake_pixelate", "pixelate", boom))
    with pytest.raises(OpError, match="fake_pixelate failed: bad image") as exc:
        registry.run_recipe(Image.new("RGB", (10, 10)), [OpCall("fake_resize"), OpCall("fake_pixelate")])
    assert exc.value.step_index == 1
    assert exc.value.op == "fake_pixelate"


def test_unknown_param_keys_fail_loudly():
    with pytest.raises(OpError, match="bogus") as exc:
        registry.validate_recipe([OpCall("noop", {"times": 1, "bogus": 2})], require_pixelate=False)
    assert exc.value.step_index == 0 and exc.value.op == "noop"


def test_register_rejects_bad_kind():
    with pytest.raises(OpError, match="KIND"):
        registry.register(fake_op("typo", "patttern", lambda p, _: p))


def test_image_op_after_pixelate_is_rejected():
    registry.register(fake_op("fake_resize", "image", lambda img, _: img))
    registry.register(fake_op("fake_pixelate", "pixelate", lambda img, _: small_pattern()))
    with pytest.raises(OpError, match="pixelate") as exc:
        registry.validate_recipe([OpCall("fake_pixelate"), OpCall("fake_resize")])
    assert exc.value.step_index == 1 and exc.value.op == "fake_resize"


def test_empty_recipe_has_no_pixelate():
    with pytest.raises(OpError, match="pixelate") as exc:
        registry.validate_recipe([])
    assert exc.value.step_index is None
