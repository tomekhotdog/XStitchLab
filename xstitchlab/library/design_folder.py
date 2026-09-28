"""`DesignFolder`: the directory `designs/<slug>/` that stores one Design.

Files inside: `prompt.md` (Brief), `input.png` (Input), `design.json` (Pattern),
`design.md` (kit notes, regenerated on every pattern write), `history.md`
(story text for the Pattern Sheet), and the exports named by `export_path`.
"""

import io
import json
import os
import re
from pathlib import Path

from PIL import Image

from xstitchlab.core.image_input import load_image
from xstitchlab.core.pattern import Pattern
from xstitchlab.library import LibraryError

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SKIP_NAMES = {"outputs", "test_renders"}
_MARKERS = ("prompt.md", "input.png", "design.json", "design.md")
_EXPORTS = {
    "png-color": "preview_color.png",
    "png-symbol": "preview_symbol.png",
    "png-realistic": "preview_realistic.png",
    "pdf": "pattern.pdf",
    "json": "design.json",
}
LAYOUTS = ("a4", "a5")


def default_root() -> Path:
    """`$XSTITCH_DESIGNS_DIR`, else `<repo>/designs`."""
    env = os.environ.get("XSTITCH_DESIGNS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "designs"


class DesignFolder:
    def __init__(self, root: Path, slug: str):
        if not SLUG_RE.match(slug):
            raise LibraryError(f"invalid slug {slug!r}: use lowercase letters, digits, and hyphens")
        self.slug = slug
        self.path = Path(root) / slug

    def __repr__(self) -> str:
        return f"DesignFolder({str(self.path)!r})"

    # --- library -------------------------------------------------------------

    @staticmethod
    def list(root: Path) -> list["DesignFolder"]:
        """Design folders under `root`, sorted by slug.

        A directory counts when it holds a prompt, input, pattern, or design.md
        (so a folder fresh from `create` is listed); names
        starting with "_" and the `outputs`/`test_renders` scratch dirs are skipped.
        """
        root = Path(root)
        if not root.is_dir():
            return []
        found = []
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("_") or child.name in _SKIP_NAMES:
                continue
            if any((child / marker).is_file() for marker in _MARKERS):
                found.append(DesignFolder(root, child.name))
        return found

    @staticmethod
    def create(root: Path, slug: str, title: str) -> "DesignFolder":
        """New folder with a `design.md` stub; LibraryError on a bad or taken slug."""
        if not SLUG_RE.match(slug):
            raise LibraryError(f"invalid slug {slug!r}: use lowercase letters, digits and hyphens")
        folder = DesignFolder(root, slug)
        if folder.path.exists():
            raise LibraryError(f"design {slug!r} already exists")
        folder.path.mkdir(parents=True)
        _write_atomic(folder.path / "design.md", f"# {title}\n".encode())
        return folder

    # --- files -------------------------------------------------------------------

    @property
    def prompt_path(self) -> Path:
        return self.path / "prompt.md"

    @property
    def input_path(self) -> Path:
        return self.path / "input.png"

    @property
    def pattern_path(self) -> Path:
        return self.path / "design.json"

    @property
    def design_md_path(self) -> Path:
        return self.path / "design.md"

    @property
    def history_path(self) -> Path:
        return self.path / "history.md"

    @property
    def has_prompt(self) -> bool:
        return self.prompt_path.is_file()

    @property
    def has_input(self) -> bool:
        return self.input_path.is_file()

    @property
    def has_pattern(self) -> bool:
        return self.pattern_path.is_file()

    @property
    def title(self) -> str:
        """`design.json` metadata title, else the first `# ` heading of design.md, else the slug."""
        if self.has_pattern:
            title = (self._pattern_json().get("metadata") or {}).get("title")
            if title:
                return str(title)
        heading = _first_heading(self._read_text(self.design_md_path))
        return heading or self.slug

    def read_prompt(self) -> str:
        return self._read_text(self.prompt_path)

    def write_prompt(self, text: str) -> None:
        _write_atomic(self.prompt_path, text.encode())

    def read_history(self) -> str:
        return self._read_text(self.history_path).strip()

    def write_history(self, text: str) -> None:
        _write_atomic(self.history_path, text.encode())

    def read_input(self) -> Image.Image:
        if not self.has_input:
            raise LibraryError(f"{self.slug} has no input.png")
        return load_image(self.input_path)

    def write_input(self, data: bytes) -> None:
        """Decode `data` (any PIL-readable format), normalise to RGB PNG; LibraryError if not an image."""
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except Exception as e:
            raise LibraryError(f"input is not a decodable image: {e}") from e
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG")
        _write_atomic(self.input_path, buf.getvalue())

    def read_pattern(self) -> Pattern:
        if not self.has_pattern:
            raise LibraryError(f"{self.slug} has no design.json")
        return Pattern.from_dict(self._pattern_json())

    def write_pattern(self, pattern: Pattern) -> None:
        """Atomically write design.json, then regenerate design.md from it."""
        from xstitchlab.library import design_md

        payload = json.dumps(pattern.to_dict(), indent=2).encode()
        _write_atomic(self.pattern_path, payload)
        _write_atomic(self.design_md_path, design_md.render(pattern, self).encode())

    def export_path(self, kind: str, layout: str | None = None) -> Path:
        """Where an export of `kind` lives; `layout` (a4|a5, default a4) applies to sheets only."""
        if kind == "sheet":
            layout = layout or "a4"
            if layout not in LAYOUTS:
                raise LibraryError(f"unknown sheet layout {layout!r} (choose from {LAYOUTS})")
            return self.path / f"pattern_sheet_{layout}.html"
        try:
            return self.path / _EXPORTS[kind]
        except KeyError:
            raise LibraryError(f"unknown export kind {kind!r} (choose from {sorted([*_EXPORTS, 'sheet'])})") from None

    def summary(self) -> dict:
        info = {
            "slug": self.slug,
            "title": self.title,
            "has_input": self.has_input,
            "has_prompt": self.has_prompt,
            "has_pattern": self.has_pattern,
            "width": None, "height": None, "colors": None, "stitches": None,
        }
        if self.has_pattern:
            pattern = self.read_pattern()
            info.update(
                width=pattern.width, height=pattern.height,
                colors=len(pattern.legend), stitches=pattern.metadata.total_stitches,
            )
        return info

    # --- internals ---------------------------------------------------------------

    def _pattern_json(self) -> dict:
        try:
            return json.loads(self.pattern_path.read_text())
        except (OSError, ValueError) as e:
            raise LibraryError(f"{self.slug}: cannot read design.json: {e}") from e

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text() if path.is_file() else ""


def _first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _write_atomic(path: Path, data: bytes) -> None:
    """Write to `<path>.tmp` then `os.replace`, so readers never see a partial file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
