"""FastAPI dependencies and wire decoding: the library root, one DesignFolder per `{slug}` route, patterns."""

from pathlib import Path

from fastapi import Depends, HTTPException

from xstitchlab.core.pattern import Pattern
from xstitchlab.library import DesignFolder

from backend.app.config import root


def get_root() -> Path:
    return root()


def get_folder(slug: str, root: Path = Depends(get_root)) -> DesignFolder:
    """The existing DesignFolder for `slug`: 404 when missing, 400 (LibraryError) on a bad slug."""
    folder = DesignFolder(root, slug)
    if not folder.path.is_dir():
        raise HTTPException(status_code=404, detail=f"design {slug!r} not found")
    return folder


def pattern_from_wire(data: dict) -> Pattern:
    """`Pattern.from_dict` for a request body: a malformed pattern is 422, not a 500."""
    try:
        return Pattern.from_dict(data)
    except (KeyError, TypeError, ValueError, IndexError) as e:
        raise HTTPException(status_code=422, detail=f"invalid pattern: {e!r}") from e
