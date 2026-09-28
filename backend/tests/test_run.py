"""`POST /api/designs/{slug}/run`: one real run of the predesigned recipe, then the error paths."""

import pytest

from xstitchlab.ops.defaults import DEFAULTS, with_overrides

from backend.tests.conftest import RIGA, make_client, seed_root


@pytest.fixture(scope="module")
def run_response():
    """One run of the predesigned recipe at width 45 (the Riga input is 1024 px, so seconds)."""
    with pytest.MonkeyPatch.context() as mp:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path
            client = make_client(seed_root(Path(tmp)), mp)
            recipe = [c.to_dict() for c in with_overrides(DEFAULTS["predesigned"], width=45)]
            yield client.post(f"/api/designs/{RIGA}/run", json={"recipe": recipe})


def test_run_returns_pattern_and_steps(run_response):
    assert run_response.status_code == 200, run_response.text
    body = run_response.json()
    pattern = body["pattern"]
    assert pattern["metadata"]["width"] == 45 and pattern["metadata"]["height"] == 45
    assert len(pattern["grid"]) == 45 and len(pattern["grid"][0]) == 45
    assert pattern["metadata"]["title"] == "Three Brothers, Riga"
    assert [c["op"] for c in pattern["recipe"]] == [c.op for c in DEFAULTS["predesigned"]]
    assert pattern["recipe"][1]["params"]["width"] == 45


def test_run_steps_have_kind_previews_and_stats(run_response):
    steps = run_response.json()["steps"]
    assert len(steps) == 7
    assert [s["kind"] for s in steps] == ["image", "pixelate"] + ["pattern"] * 5
    for step in steps:
        assert step["preview_png"].startswith("iVBOR")
        assert step["stats"]["width"] and step["stats"]["height"]
    assert "stitches" not in steps[0]["stats"]
    assert all("stitches" in s["stats"] and "colors" in s["stats"] for s in steps[1:])
    assert steps[1]["params"]["width"] == 45


def test_pattern_op_first_is_400_with_step_index(client):
    r = client.post(f"/api/designs/{RIGA}/run", json={"recipe": [{"op": "remove_isolated"}]})
    assert r.status_code == 400
    body = r.json()
    assert body["step_index"] == 0 and body["op"] == "remove_isolated"
    assert "pixelate" in body["detail"]


def test_unknown_op_is_400(client):
    r = client.post(f"/api/designs/{RIGA}/run", json={"recipe": [{"op": "teleport", "params": {}}]})
    assert r.status_code == 400
    assert r.json()["op"] == "teleport" and "unknown op" in r.json()["detail"]


def test_bad_params_is_422(client):
    r = client.post(f"/api/designs/{RIGA}/run", json={"recipe": [{"op": "pixelate", "params": {"width": "wide"}}]})
    assert r.status_code == 422
    body = r.json()
    assert body["step_index"] == 0 and body["op"] == "pixelate"
    assert body["detail"][0]["loc"] == ["width"]


def test_run_without_input_is_404(client):
    client.post("/api/designs", json={"slug": "09-blank", "title": "Blank"})
    r = client.post("/api/designs/09-blank/run", json={"recipe": [{"op": "pixelate"}]})
    assert r.status_code == 404
