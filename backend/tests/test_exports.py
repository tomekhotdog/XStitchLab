"""`/api/designs/{slug}/export/{kind}` and `/threads`."""

import json

import pytest

from backend.tests.conftest import RIGA

CASES = [
    ("sheet", None, "text/html", "pattern_sheet_a4.html"),
    ("sheet", "a5", "text/html", "pattern_sheet_a5.html"),
    ("pdf", None, "application/pdf", "pattern.pdf"),
    ("png-color", None, "image/png", "preview_color.png"),
    ("png-symbol", None, "image/png", "preview_symbol.png"),
    ("png-realistic", None, "image/png", "preview_realistic.png"),
    ("json", None, "application/json", "design.json"),
]


@pytest.mark.parametrize("kind,layout,media_type,filename", CASES)
def test_export_writes_file_and_returns_it(client, root, kind, layout, media_type, filename):
    params = {"layout": layout} if layout else {}
    r = client.get(f"/api/designs/{RIGA}/export/{kind}", params=params)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(media_type)
    assert r.headers["content-disposition"] == f'inline; filename="{filename}"'
    path = root / RIGA / filename
    assert path.is_file() and path.read_bytes() == r.content


def test_sheet_contains_title_and_history(client):
    html = client.get(f"/api/designs/{RIGA}/export/sheet").text
    assert "Three Brothers, Riga" in html
    assert "Riga" in html and "<html" in html.lower()


def test_json_export_is_canonical_pattern(client):
    body = client.get(f"/api/designs/{RIGA}/export/json").json()
    assert body == client.get(f"/api/designs/{RIGA}").json()["pattern"]


def test_unknown_kind_and_layout_are_400(client):
    assert client.get(f"/api/designs/{RIGA}/export/docx").status_code == 400
    assert client.get(f"/api/designs/{RIGA}/export/sheet", params={"layout": "a3"}).status_code == 400


def test_export_without_pattern_is_400(client):
    client.post("/api/designs", json={"slug": "10-bare", "title": "Bare"})
    assert client.get("/api/designs/10-bare/export/sheet").status_code == 400


def test_threads_has_backstitch_row_and_totals(client):
    body = client.get(f"/api/designs/{RIGA}/threads").json()
    rows, totals = body["rows"], body["totals"]
    assert len(rows) == 9  # 8 legend entries + backstitch
    assert rows[-1]["is_backstitch"] and rows[-1]["dmc_code"] == "310"
    assert any(r["is_background"] for r in rows)
    assert set(totals) == {"stitches", "meters", "skeins", "sections_60cm"}
    assert totals["stitches"] == 1203 and totals["sections_60cm"] > 0
