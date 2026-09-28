"""Backend fixtures: a temp design library seeded with the committed Riga design."""

import io
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
RIGA = "01-three-brothers-riga"
SEED_FILES = ("design.json", "input.png", "prompt.md", "design.md", "history.md")


def seed_root(into: Path) -> Path:
    """Copy the Riga design (sources only, no exports/packaging) into `<into>/designs`."""
    root = into / "designs"
    (root / RIGA).mkdir(parents=True)
    for name in SEED_FILES:
        shutil.copy(REPO / "designs" / RIGA / name, root / RIGA / name)
    return root


def make_client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A TestClient whose library root is `root` (env var and dependency override)."""
    monkeypatch.setenv("XSTITCH_DESIGNS_DIR", str(root))
    from backend.app.deps import get_root
    from backend.app.main import app

    monkeypatch.setitem(app.dependency_overrides, get_root, lambda: root)
    return TestClient(app)


def png_bytes(size=(8, 8), color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def root(tmp_path) -> Path:
    return seed_root(tmp_path)


@pytest.fixture
def client(root, monkeypatch) -> TestClient:
    return make_client(root, monkeypatch)
