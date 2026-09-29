"""`/api/designs`: the library of DesignFolders and everything inside one."""

import base64
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from xstitchlab.core.pattern import OpCall, Pattern
from xstitchlab.export import threads
from xstitchlab.library import MEDIA_TYPES, DesignFolder, export_design
from xstitchlab.ops import registry

from backend.app.deps import get_folder, get_root, pattern_from_wire
from backend.app.previews import image_png_b64, pattern_png_b64
from backend.app.schemas import (
    ApplyResponse, CreateDesign, DesignDetail, DesignSummary, PromptBody,
    RunRequest, RunResponse, SavePattern, SaveResponse, StepOut, ThreadsResponse,
)

MAX_INPUT_BYTES = 20 * 1024 * 1024

router = APIRouter(prefix="/api/designs", tags=["designs"])

THUMBNAIL_PX = 160
UNTITLED = "Untitled Pattern"


def _summary(folder: DesignFolder) -> DesignSummary:
    """`DesignFolder.summary()` plus a thumbnail: preview_color.png if exported, else a fresh render."""
    info = folder.summary()
    preview = folder.export_path("png-color")
    if preview.is_file():
        thumbnail = base64.b64encode(preview.read_bytes()).decode("ascii")
    elif folder.has_pattern:
        thumbnail = pattern_png_b64(folder.read_pattern(), THUMBNAIL_PX)
    else:
        thumbnail = None
    return DesignSummary(**info, thumbnail_png=thumbnail)


@router.get("", response_model=list[DesignSummary])
def list_designs(root: Path = Depends(get_root)):
    return [_summary(folder) for folder in DesignFolder.list(root)]


@router.post("", response_model=DesignSummary, status_code=201)
def create_design(body: CreateDesign, root: Path = Depends(get_root)):
    if DesignFolder(root, body.slug).path.exists():  # LibraryError (bad slug) -> 400
        raise HTTPException(status_code=409, detail=f"design {body.slug!r} already exists")
    return _summary(DesignFolder.create(root, body.slug, body.title))


@router.get("/{slug}", response_model=DesignDetail)
def get_design(folder: DesignFolder = Depends(get_folder)):
    return DesignDetail(
        slug=folder.slug,
        title=folder.title,
        prompt=folder.read_prompt(),
        has_input=folder.has_input,
        pattern=folder.read_pattern().to_dict() if folder.has_pattern else None,
        history=folder.read_history(),
        version=folder.pattern_version,
    )


@router.get("/{slug}/input.png")
def get_input(folder: DesignFolder = Depends(get_folder)):
    if not folder.has_input:
        raise HTTPException(status_code=404, detail=f"{folder.slug} has no input.png")
    return FileResponse(folder.input_path, media_type="image/png")


@router.put("/{slug}/input", response_model=DesignSummary)
def put_input(folder: DesignFolder = Depends(get_folder), file: UploadFile = File(...)):
    data = file.file.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise HTTPException(status_code=413, detail=f"input image larger than {MAX_INPUT_BYTES // (1024 * 1024)} MB")
    folder.write_input(data)  # LibraryError (not an image) -> 400
    return _summary(folder)


@router.put("/{slug}/prompt", response_model=PromptBody)
def put_prompt(body: PromptBody, folder: DesignFolder = Depends(get_folder)):
    folder.write_prompt(body.text)
    return body


@router.put("/{slug}/history", response_model=PromptBody)
def put_history(body: PromptBody, folder: DesignFolder = Depends(get_folder)):
    folder.write_history(body.text)
    return body


@router.put("/{slug}", response_model=SaveResponse)
def save_pattern(body: SavePattern, folder: DesignFolder = Depends(get_folder)):
    """Write design.json (canonical form) and regenerate design.md; returns the canonical pattern.

    When `version` is sent and design.json changed since that version (another tab, the CLI),
    the save is refused with 409 instead of silently overwriting the newer file.
    """
    pattern = pattern_from_wire(body.pattern)
    if body.version is not None and body.version != folder.pattern_version:
        raise HTTPException(
            status_code=409,
            detail="design.json changed on disk since you opened it. Reload the design before saving.",
        )
    folder.write_pattern(pattern)
    return SaveResponse(pattern=pattern.to_dict(), version=folder.pattern_version)


@router.post("/{slug}/run", response_model=RunResponse)
def run_recipe(body: RunRequest, folder: DesignFolder = Depends(get_folder)):
    if not folder.has_input:
        raise HTTPException(status_code=404, detail=f"{folder.slug} has no input.png")
    recipe = [OpCall(call.op, dict(call.params)) for call in body.recipe]
    result = registry.run_recipe(folder.read_input(), recipe)  # OpError -> 400 / 422
    pattern = result.pattern
    if not pattern.metadata.title or pattern.metadata.title == UNTITLED:
        pattern.metadata.title = folder.title
    steps = [
        StepOut(
            name=step.name,
            params=step.params,
            kind=registry.get(step.name).KIND,
            preview_png=(
                pattern_png_b64(step.result) if isinstance(step.result, Pattern) else image_png_b64(step.result)
            ),
            stats=step.stats,
        )
        for step in result.steps
    ]
    return RunResponse(pattern=pattern.to_dict(), steps=steps)


@router.get("/{slug}/export/{kind}")
def export(kind: str, layout: str | None = Query(None), folder: DesignFolder = Depends(get_folder)):
    """Write the export into the folder and return it inline (LibraryError on a bad kind/layout -> 400)."""
    path = export_design(folder, kind, layout)
    return FileResponse(
        path, media_type=MEDIA_TYPES[kind], filename=path.name, content_disposition_type="inline",
    )


@router.get("/{slug}/threads", response_model=ThreadsResponse)
def get_threads(folder: DesignFolder = Depends(get_folder)):
    rows = threads.estimate(folder.read_pattern())  # LibraryError (no pattern) -> 400
    return ThreadsResponse(rows=rows, totals=threads.totals(rows))
