"""Backstitch generation for cross-stitch patterns.

Backstitching adds outline stitches along color boundaries to improve
definition and visibility. Typically done with black or dark thread
after the main cross-stitches are complete.
"""

import numpy as np
from PIL import Image, ImageDraw
from dataclasses import dataclass
from typing import Optional


@dataclass
class BackstitchSettings:
    """Settings for backstitch generation."""

    # Enable backstitch
    enabled: bool = True

    # Color for backstitch lines (RGB tuple or "auto" for darkest color)
    color: tuple[int, int, int] | str = (0, 0, 0)  # Black by default

    # Which boundaries to stitch
    all_boundaries: bool = True  # All color transitions
    min_contrast: int = 50  # Minimum color difference to backstitch (0-255)

    # Line style
    include_diagonals: bool = False  # Include diagonal segments


@dataclass
class BackstitchSegment:
    """A single backstitch line segment."""
    x1: int  # Start x (in stitch coordinates)
    y1: int  # Start y
    x2: int  # End x
    y2: int  # End y

    @property
    def is_horizontal(self) -> bool:
        return self.y1 == self.y2

    @property
    def is_vertical(self) -> bool:
        return self.x1 == self.x2

    @property
    def is_diagonal(self) -> bool:
        return not self.is_horizontal and not self.is_vertical


def color_distance(c1: tuple, c2: tuple) -> float:
    """Calculate Euclidean distance between two RGB colors."""
    # Cast to int to avoid uint8 overflow on subtraction
    return np.sqrt(sum((int(a) - int(b)) ** 2 for a, b in zip(c1, c2)))


def detect_boundaries(
    indices: np.ndarray,
    palette: np.ndarray,
    min_contrast: int = 50
) -> list[BackstitchSegment]:
    """Detect color boundaries in a pattern.

    Scans the pattern for adjacent pixels with different colors and
    generates backstitch segments along those boundaries.

    Args:
        indices: 2D array of color indices
        palette: Color palette array (n_colors, 3)
        min_contrast: Minimum color distance to consider a boundary

    Returns:
        List of BackstitchSegment objects
    """
    h, w = indices.shape
    segments = []

    # Horizontal boundaries (between vertically adjacent pixels)
    for i in range(h - 1):
        for j in range(w):
            top_idx = indices[i, j]
            bottom_idx = indices[i + 1, j]

            if top_idx != bottom_idx:
                # Check contrast
                top_color = tuple(palette[top_idx])
                bottom_color = tuple(palette[bottom_idx])
                if color_distance(top_color, bottom_color) >= min_contrast:
                    # Horizontal line between row i and i+1, at column j
                    # In stitch coordinates, this is at y = i+1 (bottom of cell i)
                    segments.append(BackstitchSegment(
                        x1=j, y1=i + 1,
                        x2=j + 1, y2=i + 1
                    ))

    # Vertical boundaries (between horizontally adjacent pixels)
    for i in range(h):
        for j in range(w - 1):
            left_idx = indices[i, j]
            right_idx = indices[i, j + 1]

            if left_idx != right_idx:
                left_color = tuple(palette[left_idx])
                right_color = tuple(palette[right_idx])
                if color_distance(left_color, right_color) >= min_contrast:
                    # Vertical line between column j and j+1, at row i
                    segments.append(BackstitchSegment(
                        x1=j + 1, y1=i,
                        x2=j + 1, y2=i + 1
                    ))

    return segments


def merge_segments(segments: list[BackstitchSegment]) -> list[BackstitchSegment]:
    """Merge collinear adjacent segments into longer lines.

    This reduces the number of segments and makes the backstitch
    instructions cleaner.

    Args:
        segments: List of BackstitchSegment objects

    Returns:
        Merged list of segments
    """
    if not segments:
        return []

    # Separate horizontal and vertical segments
    horizontal = [s for s in segments if s.is_horizontal]
    vertical = [s for s in segments if s.is_vertical]
    other = [s for s in segments if s.is_diagonal]

    merged = []

    # Merge horizontal segments
    h_by_row = {}
    for s in horizontal:
        row = s.y1
        if row not in h_by_row:
            h_by_row[row] = []
        h_by_row[row].append(s)

    for row, segs in h_by_row.items():
        # Sort by x position
        segs.sort(key=lambda s: s.x1)
        # Merge adjacent
        current = segs[0]
        for s in segs[1:]:
            if s.x1 == current.x2:
                # Adjacent - extend current
                current = BackstitchSegment(
                    x1=current.x1, y1=current.y1,
                    x2=s.x2, y2=s.y2
                )
            else:
                merged.append(current)
                current = s
        merged.append(current)

    # Merge vertical segments
    v_by_col = {}
    for s in vertical:
        col = s.x1
        if col not in v_by_col:
            v_by_col[col] = []
        v_by_col[col].append(s)

    for col, segs in v_by_col.items():
        segs.sort(key=lambda s: s.y1)
        current = segs[0]
        for s in segs[1:]:
            if s.y1 == current.y2:
                current = BackstitchSegment(
                    x1=current.x1, y1=current.y1,
                    x2=s.x2, y2=s.y2
                )
            else:
                merged.append(current)
                current = s
        merged.append(current)

    # Add diagonal segments (no merging for now)
    merged.extend(other)

    return merged


def generate_backstitch(
    indices: np.ndarray,
    palette: np.ndarray,
    settings: Optional[BackstitchSettings] = None
) -> tuple[list[BackstitchSegment], dict]:
    """Generate backstitch segments for a pattern.

    Args:
        indices: 2D array of color indices
        palette: Color palette array
        settings: Backstitch settings

    Returns:
        Tuple of (list of segments, info dict)
    """
    if settings is None:
        settings = BackstitchSettings()

    if not settings.enabled:
        return [], {"enabled": False}

    # Detect boundaries
    segments = detect_boundaries(
        indices, palette, min_contrast=settings.min_contrast
    )

    # Merge adjacent segments
    segments = merge_segments(segments)

    # Filter out diagonals if not wanted
    if not settings.include_diagonals:
        segments = [s for s in segments if not s.is_diagonal]

    # Calculate stats
    total_length = sum(
        abs(s.x2 - s.x1) + abs(s.y2 - s.y1) for s in segments
    )

    info = {
        "enabled": True,
        "segment_count": len(segments),
        "total_length_stitches": total_length,
        "horizontal_segments": sum(1 for s in segments if s.is_horizontal),
        "vertical_segments": sum(1 for s in segments if s.is_vertical),
        "color": settings.color,
    }

    return segments, info


def render_backstitch(
    base_image: Image.Image,
    segments: list[BackstitchSegment],
    cell_size: int,
    color: tuple[int, int, int] = (0, 0, 0),
    line_width: int = 2
) -> Image.Image:
    """Render backstitch lines on top of a pattern image.

    Args:
        base_image: Base pattern image to draw on
        segments: List of backstitch segments
        cell_size: Size of each cell in pixels
        color: RGB color for backstitch lines
        line_width: Width of backstitch lines

    Returns:
        New image with backstitch overlay
    """
    result = base_image.copy()
    draw = ImageDraw.Draw(result)

    for seg in segments:
        # Convert stitch coordinates to pixel coordinates
        px1 = seg.x1 * cell_size
        py1 = seg.y1 * cell_size
        px2 = seg.x2 * cell_size
        py2 = seg.y2 * cell_size

        draw.line([(px1, py1), (px2, py2)], fill=color, width=line_width)

    return result


def backstitch_instructions(
    segments: list[BackstitchSegment],
    color_name: str = "Black"
) -> str:
    """Generate human-readable backstitch instructions.

    Args:
        segments: List of backstitch segments
        color_name: Name of the backstitch color

    Returns:
        Formatted instruction string
    """
    if not segments:
        return "No backstitch required."

    lines = [
        f"BACKSTITCH INSTRUCTIONS",
        f"======================",
        f"Thread: {color_name}",
        f"Total segments: {len(segments)}",
        f"",
        f"Segments (start → end):",
    ]

    # Group by type for cleaner instructions
    horizontal = [s for s in segments if s.is_horizontal]
    vertical = [s for s in segments if s.is_vertical]

    if horizontal:
        lines.append(f"\nHorizontal lines ({len(horizontal)}):")
        for s in sorted(horizontal, key=lambda x: (x.y1, x.x1)):
            lines.append(f"  Row {s.y1}: ({s.x1}, {s.y1}) → ({s.x2}, {s.y2})")

    if vertical:
        lines.append(f"\nVertical lines ({len(vertical)}):")
        for s in sorted(vertical, key=lambda x: (x.x1, x.y1)):
            lines.append(f"  Col {s.x1}: ({s.x1}, {s.y1}) → ({s.x2}, {s.y2})")

    return "\n".join(lines)
