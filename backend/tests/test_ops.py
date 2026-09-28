"""`/api/ops`, `/api/ops/apply`, `/api/recipes/defaults`, `/api/dmc`, `/api/prompt-template`."""

from backend.tests.conftest import RIGA


def test_ops_lists_registry_without_test_group(client):
    ops = client.get("/api/ops").json()
    names = [o["name"] for o in ops]
    assert "pixelate" in names and "background_to_fabric" in names
    assert "noop" not in names
    pixelate = next(o for o in ops if o["name"] == "pixelate")
    assert pixelate["kind"] == "pixelate" and pixelate["group"] and pixelate["title"]
    assert pixelate["schema"]["properties"]["width"]["maximum"] == 400
    assert set(pixelate) == {"name", "kind", "group", "title", "description", "schema"}


def test_apply_background_to_fabric(client):
    pattern = client.get(f"/api/designs/{RIGA}").json()["pattern"]
    pattern["background_index"] = None
    r = client.post("/api/ops/apply", json={"pattern": pattern, "op": "background_to_fabric", "params": {}})
    assert r.status_code == 200, r.text
    out = r.json()["pattern"]
    assert out["background_index"] is not None
    assert out["recipe"][-1] == {"op": "background_to_fabric", "params": {}}
    assert out["grid"] == pattern["grid"]


def test_apply_unknown_params_is_422(client):
    pattern = client.get(f"/api/designs/{RIGA}").json()["pattern"]
    r = client.post("/api/ops/apply", json={"pattern": pattern, "op": "background_to_fabric", "params": {"nope": 1}})
    assert r.status_code == 422
    assert r.json()["op"] == "background_to_fabric"


def test_apply_malformed_pattern_is_422(client):
    r = client.post("/api/ops/apply", json={"pattern": {"legend": []}, "op": "background_to_fabric"})
    assert r.status_code == 422
    assert "invalid pattern" in r.json()["detail"]


def test_apply_image_op_is_400(client):
    pattern = client.get(f"/api/designs/{RIGA}").json()["pattern"]
    r = client.post("/api/ops/apply", json={"pattern": pattern, "op": "quantize_image"})
    assert r.status_code == 400
    assert r.json()["step_index"] == 0


def test_default_recipes(client):
    defaults = client.get("/api/recipes/defaults").json()
    assert set(defaults) == {"predesigned", "photo"}
    assert defaults["predesigned"][1] == {"op": "pixelate", "params": {"width": 50, "sample": "majority", "steps": 1}}
    assert all(set(c) == {"op", "params"} for r in defaults.values() for c in r)


def test_dmc_palette(client):
    colors = client.get("/api/dmc").json()
    assert len(colors) > 300
    black = next(c for c in colors if c["code"] == "310")
    assert black == {"code": "310", "name": "Black", "rgb": [0, 0, 0]}


def test_prompt_template(client):
    text = client.get("/api/prompt-template").json()["text"]
    assert "<SUBJECT>" in text
    assert "pixel" in text.lower() or "cross-stitch" in text.lower()
