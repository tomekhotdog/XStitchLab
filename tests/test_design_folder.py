"""DesignFolder: listing, creation, file round-trips, atomic writes, export paths."""

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from xstitchlab.core.pattern import Pattern
from xstitchlab.library import DesignFolder, LibraryError, default_root

from tests.ops.helpers import small_pattern


def png_bytes(color=(10, 20, 30), size=(4, 3)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def root(tmp_path) -> Path:
    (tmp_path / "01-riga").mkdir()
    (tmp_path / "01-riga" / "prompt.md").write_text("a brief")
    (tmp_path / "03-bergen").mkdir()
    (tmp_path / "03-bergen" / "input.png").write_bytes(png_bytes())
    (tmp_path / "02-lubeck").mkdir()
    json.dump(small_pattern().to_dict(), (tmp_path / "02-lubeck" / "design.json").open("w"))
    (tmp_path / "_shared").mkdir()
    (tmp_path / "_shared" / "prompt.md").write_text("skip me")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "design.json").write_text("{}")
    (tmp_path / "test_renders").mkdir()
    (tmp_path / "test_renders" / "input.png").write_bytes(png_bytes())
    (tmp_path / "empty").mkdir()
    (tmp_path / "stray.txt").write_text("")
    return tmp_path


def test_list_is_sorted_and_skips_scratch_and_empty_dirs(root):
    assert [f.slug for f in DesignFolder.list(root)] == ["01-riga", "02-lubeck", "03-bergen"]
    assert DesignFolder.list(root / "missing") == []


def test_create_writes_design_md_stub(root):
    folder = DesignFolder.create(root, "06-visby", "Town Wall, Visby")
    assert folder.path == root / "06-visby"
    assert (folder.path / "design.md").read_text() == "# Town Wall, Visby\n"
    assert folder.title == "Town Wall, Visby"
    assert not (folder.has_input or folder.has_pattern or folder.has_prompt)
    # design.md is itself a marker, so a new folder is listed straight away.
    assert "06-visby" in [f.slug for f in DesignFolder.list(root)]
    folder.write_prompt("brief")
    assert "06-visby" in [f.slug for f in DesignFolder.list(root)]


@pytest.mark.parametrize("slug", ["", "Riga", "01_riga", "-riga", "riga/x", "riga x", "ríga"])
def test_create_rejects_bad_slugs(root, slug):
    with pytest.raises(LibraryError):
        DesignFolder.create(root, slug, "t")


def test_create_refuses_existing(root):
    with pytest.raises(LibraryError, match="already exists"):
        DesignFolder.create(root, "01-riga", "t")


def test_prompt_round_trip(root):
    folder = DesignFolder(root, "01-riga")
    assert folder.read_prompt() == "a brief"
    folder.write_prompt("new brief")
    assert folder.read_prompt() == "new brief"
    assert DesignFolder(root, "03-bergen").read_prompt() == ""


def test_input_round_trip_normalises_to_rgb_png(root):
    folder = DesignFolder(root, "01-riga")
    assert not folder.has_input
    with pytest.raises(LibraryError):
        folder.read_input()
    buf = io.BytesIO()
    Image.new("RGBA", (5, 2), (1, 2, 3, 255)).save(buf, format="PNG")
    folder.write_input(buf.getvalue())
    image = folder.read_input()
    assert image.mode == "RGB" and image.size == (5, 2)
    assert Image.open(folder.input_path).format == "PNG"


def test_write_input_rejects_non_images(root):
    folder = DesignFolder(root, "01-riga")
    with pytest.raises(LibraryError):
        folder.write_input(b"not an image")
    assert not folder.has_input


def test_pattern_round_trip_and_design_md_regeneration(root):
    folder = DesignFolder(root, "01-riga")
    with pytest.raises(LibraryError):
        folder.read_pattern()
    pattern = small_pattern()
    pattern.metadata.title = "Small"
    folder.write_pattern(pattern)
    loaded = folder.read_pattern()
    assert loaded.grid == pattern.grid and loaded.background_index == 0
    assert folder.title == "Small"
    md = (folder.path / "design.md").read_text()
    assert md.startswith("# Small\n")
    assert "| Black | 310 | 8 |" in md
    assert "*Note: DMC 3865 (Winter White) is the background colour and is not stitched.*" in md


def test_write_pattern_is_atomic_and_leaves_no_tmp_files(root):
    folder = DesignFolder(root, "01-riga")
    folder.write_pattern(small_pattern())
    folder.write_pattern(small_pattern())
    assert not list(folder.path.glob("*.tmp"))
    assert json.loads(folder.pattern_path.read_text())["grid"] == small_pattern().grid


def test_title_falls_back_to_heading_then_slug(root):
    assert DesignFolder(root, "03-bergen").title == "03-bergen"
    (root / "03-bergen" / "design.md").write_text("intro\n\n# No. 03 — Bryggen, Bergen\n")
    assert DesignFolder(root, "03-bergen").title == "No. 03 — Bryggen, Bergen"
    lubeck = DesignFolder(root, "02-lubeck")
    assert lubeck.title == Pattern.from_json(lubeck.pattern_path).metadata.title


def test_export_paths(root):
    folder = DesignFolder(root, "01-riga")
    assert folder.export_path("png-color") == folder.path / "preview_color.png"
    assert folder.export_path("png-symbol") == folder.path / "preview_symbol.png"
    assert folder.export_path("png-realistic") == folder.path / "preview_realistic.png"
    assert folder.export_path("pdf") == folder.path / "pattern.pdf"
    assert folder.export_path("json") == folder.path / "design.json"
    assert folder.export_path("sheet") == folder.path / "pattern_sheet_a4.html"
    assert folder.export_path("sheet", "a5") == folder.path / "pattern_sheet_a5.html"
    with pytest.raises(LibraryError):
        folder.export_path("sheet", "letter")
    with pytest.raises(LibraryError):
        folder.export_path("svg")


def test_summary(root):
    assert DesignFolder(root, "01-riga").summary() == {
        "slug": "01-riga", "title": "01-riga",
        "has_input": False, "has_prompt": True, "has_pattern": False,
        "width": None, "height": None, "colors": None, "stitches": None,
    }
    s = DesignFolder(root, "02-lubeck").summary()
    assert (s["width"], s["height"], s["colors"], s["stitches"]) == (5, 5, 3, 9)
    assert s["has_pattern"] and not s["has_input"]


def test_default_root_env_override(monkeypatch, tmp_path):
    monkeypatch.delenv("XSTITCH_DESIGNS_DIR", raising=False)
    assert default_root() == Path(__file__).resolve().parent.parent / "designs"
    monkeypatch.setenv("XSTITCH_DESIGNS_DIR", str(tmp_path))
    assert default_root() == tmp_path


def test_created_folder_is_listed_before_it_has_a_prompt(root):
    DesignFolder.create(root, "99-new", "New")
    assert "99-new" in [f.slug for f in DesignFolder.list(root)]


@pytest.mark.parametrize("slug", ["../escape", "Upper", "a/b", ""])
def test_constructor_rejects_bad_slugs(root, slug):
    with pytest.raises(LibraryError):
        DesignFolder(root, slug)
