"""`/api/designs`: listing, creation, detail, and file round-trips."""

import json
from pathlib import Path

from backend.app.config import Settings
from backend.tests.conftest import RIGA, png_bytes


def test_settings_read_designs_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XSTITCH_DESIGNS_DIR", str(tmp_path))
    assert Settings().designs_dir == tmp_path


def test_list_shows_seeded_design_with_thumbnail(client):
    designs = client.get("/api/designs").json()
    assert [d["slug"] for d in designs] == [RIGA]
    riga = designs[0]
    assert riga["title"] == "Three Brothers, Riga"
    assert riga["has_input"] and riga["has_pattern"] and riga["has_prompt"]
    assert (riga["width"], riga["height"], riga["colors"]) == (45, 45, 8)
    assert riga["thumbnail_png"] and riga["thumbnail_png"].startswith("iVBOR")  # PNG magic, base64


def test_list_uses_exported_preview_when_present(client, root):
    (root / RIGA / "preview_color.png").write_bytes(png_bytes())
    riga = client.get("/api/designs").json()[0]
    assert riga["thumbnail_png"] and len(riga["thumbnail_png"]) < 400


def test_create_then_listed(client, root):
    r = client.post("/api/designs", json={"slug": "06-visby", "title": "Town Wall, Visby"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "06-visby" and body["title"] == "Town Wall, Visby"
    assert not body["has_pattern"] and body["thumbnail_png"] is None
    assert [d["slug"] for d in client.get("/api/designs").json()] == [RIGA, "06-visby"]
    assert (root / "06-visby" / "design.md").read_text() == "# Town Wall, Visby\n"


def test_create_duplicate_is_409(client):
    r = client.post("/api/designs", json={"slug": RIGA, "title": "again"})
    assert r.status_code == 409


def test_create_bad_slug_is_400(client):
    r = client.post("/api/designs", json={"slug": "Bad Slug", "title": "x"})
    assert r.status_code == 400
    assert "slug" in r.json()["detail"]


def test_detail_has_pattern_recipe_prompt_and_history(client):
    d = client.get(f"/api/designs/{RIGA}").json()
    assert d["slug"] == RIGA and d["title"] == "Three Brothers, Riga"
    assert d["has_input"] is True
    assert d["prompt"].startswith("Create a pixel art illustration")
    assert d["history"]
    pattern = d["pattern"]
    assert set(pattern) == {"metadata", "legend", "grid", "backstitch", "background_index", "recipe"}
    assert [c["op"] for c in pattern["recipe"]][1] == "pixelate"
    assert len(pattern["grid"]) == 45 and pattern["backstitch"]


def test_detail_without_pattern(client):
    client.post("/api/designs", json={"slug": "07-empty", "title": "Empty"})
    d = client.get("/api/designs/07-empty").json()
    assert d["pattern"] is None and d["prompt"] == "" and d["history"] == "" and not d["has_input"]


def test_unknown_slug_is_404(client):
    assert client.get("/api/designs/99-nowhere").status_code == 404
    assert client.get("/api/designs/99-nowhere/input.png").status_code == 404
    assert client.put("/api/designs/99-nowhere/prompt", json={"text": "x"}).status_code == 404


def test_prompt_and_history_round_trip(client, root):
    assert client.put(f"/api/designs/{RIGA}/prompt", json={"text": "new brief"}).json() == {"text": "new brief"}
    assert (root / RIGA / "prompt.md").read_text() == "new brief"
    assert client.put(f"/api/designs/{RIGA}/history", json={"text": "a story"}).json() == {"text": "a story"}
    assert (root / RIGA / "history.md").read_text() == "a story"
    d = client.get(f"/api/designs/{RIGA}").json()
    assert d["prompt"] == "new brief" and d["history"] == "a story"


def test_get_input_png(client):
    r = client.get(f"/api/designs/{RIGA}/input.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_put_input_with_png(client, root):
    client.post("/api/designs", json={"slug": "08-new", "title": "New"})
    r = client.put("/api/designs/08-new/input", files={"file": ("in.png", png_bytes(), "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["has_input"] is True
    assert (root / "08-new" / "input.png").is_file()


def test_put_input_with_text_is_400(client):
    r = client.put(f"/api/designs/{RIGA}/input", files={"file": ("in.txt", b"not an image", "text/plain")})
    assert r.status_code == 400
    assert "image" in r.json()["detail"]


def test_save_pattern_rewrites_design_json_and_design_md(client, root):
    pattern = client.get(f"/api/designs/{RIGA}").json()["pattern"]
    pattern["grid"][0][0] = 1
    pattern["legend"][0]["stitch_count"] = 999  # stale count: recomputed on save
    md_before = (root / RIGA / "design.md").read_text()

    r = client.put(f"/api/designs/{RIGA}", json={"pattern": pattern})
    assert r.status_code == 200, r.text
    saved = r.json()["pattern"]
    assert saved["grid"][0][0] == 1
    assert saved["legend"][0]["stitch_count"] != 999

    on_disk = json.loads((root / RIGA / "design.json").read_text())
    assert on_disk == saved
    md_after = (root / RIGA / "design.md").read_text()
    assert md_after != md_before and md_after.startswith("# ") and "## Thread Table" in md_after


def test_save_malformed_pattern_is_422(client):
    r = client.put(f"/api/designs/{RIGA}", json={"pattern": {"legend": []}})
    assert r.status_code == 422
