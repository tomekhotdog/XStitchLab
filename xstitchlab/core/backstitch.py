"""Backstitch boundary detection and rendering.

Backstitching adds outline stitches along colour boundaries. The
`generate_backstitch` op merges what `detect_boundaries` finds; the segments
it emits use grid-corner coordinates like `pattern.Segment`.
"""

import numpy as np
from PIL import Image, ImageDraw
from dataclasses import dataclass


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


def render_backstitch(
    base_image: Image.Image,
    segments,
    cell_size: int,
    color: tuple[int, int, int] = (0, 0, 0),
    line_width: int = 2
) -> Image.Image:
    """Render backstitch lines on top of a pattern image.

    Args:
        base_image: Base pattern image to draw on
        segments: Segments with x1/y1/x2/y2 in grid-corner units
            (`BackstitchSegment` or `pattern.Segment`)
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
