"""Pattern processing service - wraps xstitchlab.core functionality."""

import sys
import io
import base64
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np
import uuid

# Add parent project to path so we can import xstitchlab
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def image_to_base64(img: Image.Image, target_size: tuple[int, int] = None, max_size: int = 400) -> str:
    """Convert PIL Image to base64 data URL for frontend display.

    Args:
        img: PIL Image to convert
        target_size: Optional (width, height) to resize to exactly (uses NEAREST for pixel art)
        max_size: Minimum display size - upscales small images
    """
    # Resize to target size if specified (for consistent pipeline display)
    if target_size:
        img = img.resize(target_size, Image.Resampling.NEAREST)
    else:
        # Upscale small images for better display
        w, h = img.size
        if w < max_size or h < max_size:
            scale = max(max_size // w, max_size // h, 1)
            if scale > 1:
                img = img.resize((w * scale, h * scale), Image.Resampling.NEAREST)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

from xstitchlab.core.pixelator import (
    pixelate,
    get_color_indices,
)
from xstitchlab.core.color_mapper import ColorMapper
from xstitchlab.core.pattern import Pattern, PatternMetadata, ColorLegendEntry
from xstitchlab.core.adjuster import AdjustmentSettings, adjust_pattern
from xstitchlab.core.backstitch import BackstitchSettings, generate_backstitch

# Standard symbols for pattern display
SYMBOLS = [
    "●", "■", "▲", "◆", "★", "♦", "♣", "♠", "♥", "○",
    "□", "△", "◇", "☆", "◐", "◑", "◒", "◓", "⬟", "⬡",
    "⊕", "⊗", "⊙", "⊚", "⊛", "⊜", "⊝", "⧫", "⬢", "⬣",
    "▼", "◀", "▶", "▷", "◁", "⬤", "⬥", "⬦", "⬧", "⬨",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"
]

# In-memory pattern storage (for MVP - would use database in production)
_patterns: dict[str, dict] = {}


def process_image_to_pattern(
    image: Image.Image,
    title: str = "Untitled",
    grid_size: int = 50,
    num_colors: int = 8,
    mode: str = "photo",
    quantize_method: str = "kmeans",
    dithering: bool = False,
    color_space: str = "lab",
    resize_method: str = "nearest",
    resize_steps: int = 1,
    merge_threshold: int = 0,
    fabric_count: int = 14,
    # Adjustment settings
    fill_holes: bool = True,
    snap_diagonals: bool = True,
    connect_lines: bool = True,
    rectangularize: bool = True,
    remove_isolated: bool = True,
    min_region_size: int = 1,
    smoothing_iterations: int = 0,
    straighten_edges: bool = False,
    # Regularity settings
    regularize_rectangles: bool = False,
    min_rectangle_group_size: int = 3,
    enforce_repetition: bool = False,
    repetition_similarity_threshold: float = 0.8,
    # Backstitch settings
    backstitch_enabled: bool = False,
    backstitch_color: str = "auto",
    backstitch_contrast: int = 50,
    backstitch_diagonals: bool = False,
) -> dict:
    """Process an image into a cross-stitch pattern.

    Returns dict with pattern data and unique ID.
    """
    # Convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")

    use_lab = color_space == "lab"

    # Pipeline stages - store raw images first, convert to base64 at end with consistent size
    stage_images = {
        "original": image.copy(),
    }

    # Build adjustment settings
    adjustment_settings = AdjustmentSettings(
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
    )

    if mode == "photo":
        # Photo pipeline: resize + quantize
        from xstitchlab.core.pixelator import (
            resize_to_grid, quantize_colors_kmeans, quantize_colors_median_cut,
            apply_dithering, boundary_preserving_resize, multi_step_resize,
            merge_similar_colors
        )

        # Step 1: Resize using selected method
        if resize_method == "majority":
            if resize_steps > 1:
                resized = multi_step_resize(image, grid_size, num_steps=resize_steps, mode="majority")
            else:
                resized = boundary_preserving_resize(image, grid_size)
        else:
            resample = "nearest" if resize_method == "nearest" else "lanczos"
            resized = resize_to_grid(image, grid_size, resample_method=resample)

        # Step 2: Quantize colors
        if dithering:
            pixelated = apply_dithering(resized, num_colors, dither=True)
            arr = np.array(pixelated)
            unique_colors = np.unique(arr.reshape(-1, 3), axis=0)
            palette = unique_colors[:num_colors]
        elif quantize_method == "median_cut":
            pixelated, palette = quantize_colors_median_cut(resized, num_colors)
        else:
            pixelated, palette = quantize_colors_kmeans(resized, num_colors)

        color_indices = get_color_indices(pixelated, palette)

        # Step 3: Optionally merge similar colors
        if merge_threshold > 0:
            palette, color_indices = merge_similar_colors(palette, color_indices, threshold=merge_threshold)
            # Reconstruct image with merged palette
            merged_arr = palette[color_indices]
            pixelated = Image.fromarray(merged_arr.astype(np.uint8))

        # Store pixelated stage
        stage_images["pixelated"] = pixelated

    else:
        # Pre-designed pipeline: quantize at full res, then resize
        from sklearn.cluster import MiniBatchKMeans
        from xstitchlab.core.pixelator import (
            boundary_preserving_resize, multi_step_resize,
            quantize_colors_median_cut, merge_similar_colors
        )

        arr = np.array(image)
        h, w = arr.shape[:2]
        pixels = arr.reshape(-1, 3).astype(np.float32)

        # Quantize at full resolution (use MiniBatchKMeans for speed on large images)
        if quantize_method == "median_cut":
            quantized, palette = quantize_colors_median_cut(image, num_colors)
        else:
            # MiniBatchKMeans is ~18x faster than KMeans on large images
            kmeans = MiniBatchKMeans(n_clusters=num_colors, random_state=42, n_init=1, batch_size=1024)
            labels = kmeans.fit_predict(pixels)
            palette = kmeans.cluster_centers_.astype(np.uint8)
            clean_pixels = palette[labels]
            clean_arr = clean_pixels.reshape(h, w, 3)
            quantized = Image.fromarray(clean_arr)

        # Store quantized stage
        stage_images["quantized"] = quantized

        # Resize if needed
        if grid_size and w > grid_size:
            if resize_steps > 1:
                resized = multi_step_resize(quantized, grid_size, num_steps=resize_steps, mode="majority")
            else:
                resized = boundary_preserving_resize(quantized, grid_size, mode="majority")
            stage_images["resized"] = resized
        else:
            resized = quantized

        color_indices = get_color_indices(resized, palette)

        # Optionally merge similar colors
        if merge_threshold > 0:
            palette, color_indices = merge_similar_colors(palette, color_indices, threshold=merge_threshold)

    # Apply adjustments
    color_indices, palette, adjustment_stats = adjust_pattern(
        color_indices, palette, adjustment_settings
    )

    # Store post-adjustment stage (final pattern size)
    post_adjust_arr = palette[color_indices]
    post_adjust_img = Image.fromarray(post_adjust_arr.astype(np.uint8))
    stage_images["adjusted"] = post_adjust_img

    # Get final pattern dimensions for consistent pipeline display
    pattern_height, pattern_width = color_indices.shape

    # Scale up to see individual pixels clearly (250% zoom, min 400px)
    display_min_size = 400
    scale = max(display_min_size / min(pattern_width, pattern_height), 2.5)
    display_size = (int(pattern_width * scale), int(pattern_height * scale))

    # Convert all stage images to base64 with consistent display size
    pipeline_stages = {
        key: image_to_base64(img, target_size=display_size)
        for key, img in stage_images.items()
    }

    # Map to DMC colors
    mapper = ColorMapper(use_lab=use_lab)
    dmc_colors = mapper.map_palette(palette)

    # Create pattern
    legend = []
    for i, dmc in enumerate(dmc_colors):
        symbol = SYMBOLS[i] if i < len(SYMBOLS) else str(i)
        legend.append(ColorLegendEntry(dmc_color=dmc, symbol=symbol, stitch_count=0))

    pattern = Pattern(
        grid=color_indices.tolist(),
        legend=legend,
        metadata=PatternMetadata(title=title, fabric_count=fabric_count)
    )
    pattern.count_stitches()

    # Handle backstitch
    backstitch_segments = []
    if backstitch_enabled:
        # Parse backstitch color
        if backstitch_color == "auto":
            bs_color = "auto"
        elif backstitch_color.startswith("#"):
            # Parse hex color
            hex_color = backstitch_color.lstrip("#")
            bs_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:
            bs_color = (0, 0, 0)  # Default to black

        bs_settings = BackstitchSettings(
            enabled=True,
            color=bs_color,
            min_contrast=backstitch_contrast,
            include_diagonals=backstitch_diagonals,
        )
        segments, _ = generate_backstitch(color_indices, palette, bs_settings)
        backstitch_segments = [
            {"start": (s.x1, s.y1), "end": (s.x2, s.y2)}
            for s in segments
        ]

    # Generate unique ID and store
    pattern_id = str(uuid.uuid4())[:8]
    pattern_data = pattern.to_dict()
    pattern_data["id"] = pattern_id
    pattern_data["backstitch_segments"] = backstitch_segments
    pattern_data["pipeline_stages"] = pipeline_stages
    pattern_data["adjustment_stats"] = adjustment_stats

    _patterns[pattern_id] = pattern_data

    return pattern_data


def get_pattern(pattern_id: str) -> Optional[dict]:
    """Get pattern by ID."""
    return _patterns.get(pattern_id)


def update_pattern(pattern_id: str, grid: Optional[list] = None) -> Optional[dict]:
    """Update pattern grid."""
    if pattern_id not in _patterns:
        return None

    pattern_data = _patterns[pattern_id]

    if grid is not None:
        pattern_data["grid"] = grid
        # Recalculate stitch counts
        pattern = Pattern.from_dict(pattern_data)
        pattern.count_stitches()
        pattern_data = pattern.to_dict()
        pattern_data["id"] = pattern_id

    _patterns[pattern_id] = pattern_data
    return pattern_data


def list_patterns() -> list[dict]:
    """List all patterns (summary only)."""
    return [
        {
            "id": pid,
            "title": p["metadata"]["title"],
            "width": p["metadata"]["width"],
            "height": p["metadata"]["height"],
        }
        for pid, p in _patterns.items()
    ]
