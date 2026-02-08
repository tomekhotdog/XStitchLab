"""Pattern API routes."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io

from ..services.pattern_service import (
    process_image_to_pattern,
    get_pattern,
    update_pattern,
    list_patterns,
)
from ..schemas.patterns import PatternSchema, PatternUpdateRequest

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.post("/from-image")
async def create_pattern_from_image(
    file: UploadFile = File(...),
    title: str = Form(default="Untitled"),
    grid_size: int = Form(default=50),
    num_colors: int = Form(default=8),
    mode: str = Form(default="photo"),
    quantize_method: str = Form(default="kmeans"),
    dithering: bool = Form(default=False),
    color_space: str = Form(default="lab"),
    resize_method: str = Form(default="nearest"),
    resize_steps: int = Form(default=3),
    merge_threshold: int = Form(default=0),
    fabric_count: int = Form(default=14),
    # Adjustment settings
    fill_holes: bool = Form(default=True),
    snap_diagonals: bool = Form(default=True),
    connect_lines: bool = Form(default=True),
    rectangularize: bool = Form(default=True),
    remove_isolated: bool = Form(default=True),
    min_region_size: int = Form(default=1),
    smoothing_iterations: int = Form(default=0),
    straighten_edges: bool = Form(default=False),
    # Regularity settings
    regularize_rectangles: bool = Form(default=False),
    min_rectangle_group_size: int = Form(default=3),
    enforce_repetition: bool = Form(default=False),
    repetition_similarity_threshold: float = Form(default=0.8),
    # Backstitch settings
    backstitch_enabled: bool = Form(default=False),
    backstitch_color: str = Form(default="auto"),
    backstitch_contrast: int = Form(default=50),
    backstitch_diagonals: bool = Form(default=False),
):
    """Upload an image and create a cross-stitch pattern."""
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read image
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read image: {e}")

    # Process image
    try:
        pattern_data = process_image_to_pattern(
            image=image,
            title=title,
            grid_size=grid_size,
            num_colors=num_colors,
            mode=mode,
            quantize_method=quantize_method,
            dithering=dithering,
            color_space=color_space,
            resize_method=resize_method,
            resize_steps=resize_steps,
            merge_threshold=merge_threshold,
            fabric_count=fabric_count,
            # Adjustment settings
            fill_holes=fill_holes,
            snap_diagonals=snap_diagonals,
            connect_lines=connect_lines,
            rectangularize=rectangularize,
            remove_isolated=remove_isolated,
            min_region_size=min_region_size,
            smoothing_iterations=smoothing_iterations,
            straighten_edges=straighten_edges,
            # Regularity settings
            regularize_rectangles=regularize_rectangles,
            min_rectangle_group_size=min_rectangle_group_size,
            enforce_repetition=enforce_repetition,
            repetition_similarity_threshold=repetition_similarity_threshold,
            # Backstitch settings
            backstitch_enabled=backstitch_enabled,
            backstitch_color=backstitch_color,
            backstitch_contrast=backstitch_contrast,
            backstitch_diagonals=backstitch_diagonals,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    return pattern_data


@router.get("/")
async def list_all_patterns():
    """List all stored patterns."""
    return list_patterns()


@router.get("/{pattern_id}")
async def get_pattern_by_id(pattern_id: str):
    """Get a pattern by ID."""
    pattern = get_pattern(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern


@router.put("/{pattern_id}")
async def update_pattern_by_id(pattern_id: str, request: PatternUpdateRequest):
    """Update a pattern (e.g., after editing)."""
    pattern = update_pattern(pattern_id, grid=request.grid)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern
