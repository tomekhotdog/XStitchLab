"""Export API routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any
from PIL import Image
import io
import tempfile

# Add parent project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from xstitchlab.core.pattern import Pattern
from xstitchlab.core.visualizer import (
    render_color_preview,
    render_symbol_grid,
    create_pattern_sheet,
    render_thread_realistic,
)
from xstitchlab.core.thread_calc import ThreadCalculator
from xstitchlab.export.pdf_exporter import PDFExporter

from ..services.pattern_service import get_pattern

router = APIRouter(prefix="/api/patterns", tags=["export"])


class PatternExportRequest(BaseModel):
    """Request body for direct pattern export."""
    grid: list[list[int]]
    legend: list[dict]
    metadata: dict
    backstitch_segments: Optional[list[dict]] = None

    class Config:
        extra = "allow"  # Allow additional fields


def _get_pattern_or_404(pattern_id: str) -> Pattern:
    """Get pattern by ID or raise 404."""
    pattern_data = get_pattern(pattern_id)
    if not pattern_data:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return Pattern.from_dict(pattern_data)


# === Direct export endpoints (for imported patterns) ===
# These MUST come before the parameterized routes to avoid conflicts

@router.post("/direct/export/png")
async def export_png_direct(
    pattern_data: PatternExportRequest,
    mode: str = Query(default="color", description="Export mode: color, symbol, sheet, realistic"),
    cell_size: int = Query(default=20, ge=5, le=50),
    show_grid: bool = Query(default=True),
):
    """Export pattern as PNG from provided data (no storage required)."""
    try:
        pattern = Pattern.from_dict(pattern_data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid pattern data: {e}")

    if mode == "color":
        img = render_color_preview(pattern, cell_size=cell_size, show_grid=show_grid)
    elif mode == "symbol":
        img = render_symbol_grid(pattern, cell_size=cell_size, show_grid=show_grid)
    elif mode == "sheet":
        img = create_pattern_sheet(pattern)
    elif mode == "realistic":
        img = render_thread_realistic(pattern, cell_size=cell_size)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    title = pattern_data.metadata.get("title", "pattern") if pattern_data.metadata else "pattern"
    filename = f"{title}_{mode}.png"
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/direct/export/pdf")
async def export_pdf_direct(
    pattern_data: PatternExportRequest,
    include_preview: bool = Query(default=True),
    include_shopping_list: bool = Query(default=True),
):
    """Export pattern as PDF from provided data (no storage required)."""
    try:
        pattern = Pattern.from_dict(pattern_data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid pattern data: {e}")

    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = PDFExporter(tmpdir)
        pdf_path = exporter.export_pattern(
            pattern,
            base_name=pattern.metadata.title or "pattern",
            include_preview=include_preview,
            include_shopping_list=include_shopping_list,
            fabric_count=pattern.metadata.fabric_count,
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    title = pattern_data.metadata.get("title", "pattern") if pattern_data.metadata else "pattern"
    filename = f"{title}_pattern.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# === Parameterized routes (pattern ID based) ===

@router.get("/{pattern_id}/export/png")
async def export_png(
    pattern_id: str,
    mode: str = Query(default="color", description="Export mode: color, symbol, sheet, realistic"),
    cell_size: int = Query(default=20, ge=5, le=50),
    show_grid: bool = Query(default=True),
):
    """Export pattern as PNG image."""
    pattern = _get_pattern_or_404(pattern_id)

    if mode == "color":
        img = render_color_preview(pattern, cell_size=cell_size, show_grid=show_grid)
    elif mode == "symbol":
        img = render_symbol_grid(pattern, cell_size=cell_size, show_grid=show_grid)
    elif mode == "sheet":
        img = create_pattern_sheet(pattern)
    elif mode == "realistic":
        img = render_thread_realistic(pattern, cell_size=cell_size)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    # Convert to bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    filename = f"{pattern.metadata.title}_{mode}.png"
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{pattern_id}/export/pdf")
async def export_pdf(
    pattern_id: str,
    include_preview: bool = Query(default=True),
    include_shopping_list: bool = Query(default=True),
):
    """Export pattern as PDF document."""
    pattern = _get_pattern_or_404(pattern_id)

    # Create PDF in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = PDFExporter(tmpdir)
        pdf_path = exporter.export_pattern(
            pattern,
            base_name=pattern.metadata.title or "pattern",
            include_preview=include_preview,
            include_shopping_list=include_shopping_list,
            fabric_count=pattern.metadata.fabric_count,
        )

        # Read PDF bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    filename = f"{pattern.metadata.title}_pattern.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{pattern_id}/export/json")
async def export_json(pattern_id: str):
    """Export pattern as JSON."""
    pattern_data = get_pattern(pattern_id)
    if not pattern_data:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Return JSON directly (FastAPI handles serialization)
    return pattern_data


@router.get("/{pattern_id}/threads")
async def get_thread_estimates(
    pattern_id: str,
    fabric_count: int = Query(default=14, ge=11, le=22),
):
    """Get thread estimates for pattern."""
    pattern = _get_pattern_or_404(pattern_id)

    calc = ThreadCalculator(fabric_count=fabric_count)
    estimates = calc.estimate_all(pattern)

    # Find background color (lightest by luminance) - excluded from totals
    # since background is left unstitched in cross-stitch
    background_idx = None
    max_brightness = -1
    for idx, e in enumerate(estimates):
        r, g, b = e["rgb"]
        brightness = 0.299 * r + 0.587 * g + 0.114 * b
        if brightness > max_brightness:
            max_brightness = brightness
            background_idx = idx

    # Mark background thread
    for idx, e in enumerate(estimates):
        e["is_background"] = (idx == background_idx)

    # Calculate totals excluding background
    total_stitches = sum(e["stitch_count"] for idx, e in enumerate(estimates) if idx != background_idx)
    total_meters = sum(e["meters"] for idx, e in enumerate(estimates) if idx != background_idx)
    total_skeins = sum(e["skeins"] for idx, e in enumerate(estimates) if idx != background_idx)

    return {
        "fabric_count": fabric_count,
        "threads": estimates,
        "totals": {
            "stitches": total_stitches,
            "meters": round(total_meters, 1),
            "skeins": total_skeins,
        }
    }
