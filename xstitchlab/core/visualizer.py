"""Visualization tools for cross-stitch patterns."""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import Optional
from pathlib import Path

from .pattern import Pattern, DMCColor


def get_font(size: int = 12) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font for drawing, with fallback to default."""
    try:
        # Try common system fonts
        font_paths = [
            "/System/Library/Fonts/Menlo.ttc",  # macOS
            "/System/Library/Fonts/Monaco.ttf",  # macOS
            "C:/Windows/Fonts/consola.ttf",  # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux
        ]
        for path in font_paths:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    except Exception:
        pass

    return ImageFont.load_default()


def render_color_preview(
    pattern: Pattern,
    cell_size: int = 10,
    show_grid: bool = True,
    grid_major: int = 10,
    backstitch_segments: Optional[list[dict]] = None,
) -> Image.Image:
    """Render pattern as colored blocks (how it will look when stitched).

    Args:
        pattern: The Pattern object
        cell_size: Size of each cell in pixels
        show_grid: Whether to show grid lines
        grid_major: Draw thicker lines every N cells
        backstitch_segments: Optional list of backstitch line segments,
            each a dict with 'start' and 'end' keys as [x, y] grid coords.

    Returns:
        PIL Image with color preview
    """
    width = pattern.metadata.width * cell_size
    height = pattern.metadata.height * cell_size

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw colored cells
    for y, row in enumerate(pattern.grid):
        for x, color_idx in enumerate(row):
            if 0 <= color_idx < len(pattern.legend):
                color = pattern.legend[color_idx].dmc_color.rgb
                x0, y0 = x * cell_size, y * cell_size
                x1, y1 = x0 + cell_size, y0 + cell_size
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=color)

    # Draw grid
    if show_grid:
        grid_color = (200, 200, 200)
        major_color = (100, 100, 100)

        for i in range(pattern.metadata.width + 1):
            x = i * cell_size
            color = major_color if i % grid_major == 0 else grid_color
            draw.line([(x, 0), (x, height)], fill=color)

        for i in range(pattern.metadata.height + 1):
            y = i * cell_size
            color = major_color if i % grid_major == 0 else grid_color
            draw.line([(0, y), (width, y)], fill=color)

    # Draw backstitch outlines
    if backstitch_segments:
        bs_width = max(1, int(cell_size * 0.15))
        for seg in backstitch_segments:
            sx, sy = seg["start"]
            ex, ey = seg["end"]
            draw.line(
                [(sx * cell_size, sy * cell_size), (ex * cell_size, ey * cell_size)],
                fill=(10, 10, 10), width=bs_width,
            )

    return img


def render_symbol_grid(
    pattern: Pattern,
    cell_size: int = 20,
    show_grid: bool = True,
    grid_major: int = 10,
    font_size: Optional[int] = None
) -> Image.Image:
    """Render pattern as symbol grid for stitching.

    Args:
        pattern: The Pattern object
        cell_size: Size of each cell in pixels
        show_grid: Whether to show grid lines
        grid_major: Draw thicker lines every N cells
        font_size: Font size for symbols (auto-calculated if None)

    Returns:
        PIL Image with symbol grid
    """
    width = pattern.metadata.width * cell_size
    height = pattern.metadata.height * cell_size

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    if font_size is None:
        font_size = max(8, cell_size - 6)
    font = get_font(font_size)

    # Draw symbols
    for y, row in enumerate(pattern.grid):
        for x, color_idx in enumerate(row):
            if 0 <= color_idx < len(pattern.legend):
                symbol = pattern.legend[color_idx].symbol
                cx = x * cell_size + cell_size // 2
                cy = y * cell_size + cell_size // 2

                # Get text bounding box for centering
                bbox = draw.textbbox((0, 0), symbol, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

                draw.text(
                    (cx - tw // 2, cy - th // 2),
                    symbol,
                    fill=(0, 0, 0),
                    font=font
                )

    # Draw grid
    if show_grid:
        grid_color = (220, 220, 220)
        major_color = (128, 128, 128)

        for i in range(pattern.metadata.width + 1):
            x = i * cell_size
            color = major_color if i % grid_major == 0 else grid_color
            line_width = 2 if i % grid_major == 0 else 1
            draw.line([(x, 0), (x, height)], fill=color, width=line_width)

        for i in range(pattern.metadata.height + 1):
            y = i * cell_size
            color = major_color if i % grid_major == 0 else grid_color
            line_width = 2 if i % grid_major == 0 else 1
            draw.line([(0, y), (width, y)], fill=color, width=line_width)

    return img


def render_thread_realistic(
    pattern: Pattern,
    cell_size: int = 20,
    thread_width: float = 0.7,
    backstitch_segments: Optional[list[dict]] = None,
) -> Image.Image:
    """Render pattern with realistic thread texture via 2x supersampling.

    Produces an image that simulates how the finished cross-stitch looks:
    cream Aida fabric with textured X stitches showing thread depth,
    anti-aliased strokes, and subtle shading.

    Args:
        pattern: The Pattern object
        cell_size: Size of each cell in output pixels (rendered at 2x internally)
        thread_width: Width of thread relative to cell (0-1)
        backstitch_segments: Optional list of backstitch line segments,
            each a dict with 'start' and 'end' keys as [x, y] grid coords.

    Returns:
        PIL Image with realistic thread appearance
    """
    scale = 2  # Supersample factor for anti-aliasing
    cs = cell_size * scale  # Internal cell size
    pw = pattern.metadata.width
    ph = pattern.metadata.height
    w, h = pw * cs, ph * cs

    # --- Fabric base with woven texture ---
    fabric_base = (245, 240, 235)
    fabric_arr = np.full((h, w, 3), fabric_base, dtype=np.uint8)

    # Aida weave: subtle checkerboard at the thread-intersection scale
    weave_period = max(2, cs // 6)
    yy, xx = np.ogrid[:h, :w]
    checker = ((yy // weave_period) + (xx // weave_period)) % 2 == 0
    fabric_arr[checker] = np.clip(
        fabric_arr[checker].astype(np.int16) - 6, 0, 255
    ).astype(np.uint8)

    # Tiny holes at cell corners (Aida fabric holes)
    hole_r = max(1, cs // 12)
    for gy in range(ph + 1):
        for gx in range(pw + 1):
            cy, cx = gy * cs, gx * cs
            y0 = max(0, cy - hole_r)
            y1 = min(h, cy + hole_r + 1)
            x0 = max(0, cx - hole_r)
            x1 = min(w, cx + hole_r + 1)
            # Darken the hole area
            patch = fabric_arr[y0:y1, x0:x1].astype(np.int16) - 20
            fabric_arr[y0:y1, x0:x1] = np.clip(patch, 0, 255).astype(np.uint8)

    img = Image.fromarray(fabric_arr)
    draw = ImageDraw.Draw(img)

    # --- Thread parameters ---
    margin = int(cs * (1 - thread_width) / 2)
    tw = max(2, int(cs * thread_width * 0.35))  # Main thread stroke width

    # --- Draw stitches ---
    for y, row in enumerate(pattern.grid):
        for x, color_idx in enumerate(row):
            if not (0 <= color_idx < len(pattern.legend)):
                continue

            r, g, b = pattern.legend[color_idx].dmc_color.rgb
            cx0 = x * cs + margin
            cy0 = y * cs + margin
            cx1 = (x + 1) * cs - margin
            cy1 = (y + 1) * cs - margin

            # Shadow color (darker, semi-transparent effect via blend)
            sr = max(0, int(r * 0.55))
            sg = max(0, int(g * 0.55))
            sb = max(0, int(b * 0.55))

            # Highlight color (lighter)
            hr = min(255, int(r + (255 - r) * 0.3))
            hg = min(255, int(g + (255 - g) * 0.3))
            hb = min(255, int(b + (255 - b) * 0.3))

            shadow_offset = max(1, tw // 3)

            # Bottom strand: bottom-left → top-right (drawn first, underneath)
            # Shadow
            draw.line(
                [(cx0 + shadow_offset, cy1 + shadow_offset),
                 (cx1 + shadow_offset, cy0 + shadow_offset)],
                fill=(sr, sg, sb), width=tw
            )
            # Main stroke
            draw.line(
                [(cx0, cy1), (cx1, cy0)],
                fill=(r, g, b), width=tw
            )
            # Highlight along upper edge
            draw.line(
                [(cx0 - shadow_offset // 2, cy1 - shadow_offset // 2),
                 (cx1 - shadow_offset // 2, cy0 - shadow_offset // 2)],
                fill=(hr, hg, hb), width=max(1, tw // 3)
            )

            # Top strand: top-left → bottom-right (drawn second, on top)
            # Shadow
            draw.line(
                [(cx0 + shadow_offset, cy0 + shadow_offset),
                 (cx1 + shadow_offset, cy1 + shadow_offset)],
                fill=(sr, sg, sb), width=tw
            )
            # Main stroke
            draw.line(
                [(cx0, cy0), (cx1, cy1)],
                fill=(r, g, b), width=tw
            )
            # Highlight along upper edge
            draw.line(
                [(cx0 - shadow_offset // 2, cy0 - shadow_offset // 2),
                 (cx1 - shadow_offset // 2, cy1 - shadow_offset // 2)],
                fill=(hr, hg, hb), width=max(1, tw // 3)
            )

    # --- Backstitch outlines (drawn on top of all stitches) ---
    if backstitch_segments:
        bs_width = max(2, int(cs * 0.12))
        bs_shadow = max(1, bs_width // 2)

        for seg in backstitch_segments:
            sx, sy = seg["start"]
            ex, ey = seg["end"]
            # Coordinates are in grid-corner units → multiply by cell size
            px0, py0 = int(sx * cs), int(sy * cs)
            px1, py1 = int(ex * cs), int(ey * cs)

            # Shadow underneath for depth
            draw.line(
                [(px0 + bs_shadow, py0 + bs_shadow),
                 (px1 + bs_shadow, py1 + bs_shadow)],
                fill=(40, 40, 40), width=bs_width,
            )
            # Main black backstitch line
            draw.line(
                [(px0, py0), (px1, py1)],
                fill=(10, 10, 10), width=bs_width,
            )

    # --- Downsample with LANCZOS for anti-aliasing ---
    final_w = pw * cell_size
    final_h = ph * cell_size
    img = img.resize((final_w, final_h), Image.Resampling.LANCZOS)

    # --- Pad to square (centre pattern on fabric-coloured background) ---
    if final_w != final_h:
        side = max(final_w, final_h)
        square_img = Image.new("RGB", (side, side), (245, 240, 235))
        offset_x = (side - final_w) // 2
        offset_y = (side - final_h) // 2
        square_img.paste(img, (offset_x, offset_y))
        img = square_img

    return img


def render_legend(
    pattern: Pattern,
    cell_width: int = 200,
    row_height: int = 30
) -> Image.Image:
    """Render color legend with symbols, DMC codes, and names.

    Args:
        pattern: The Pattern object
        cell_width: Width of each legend entry
        row_height: Height of each row

    Returns:
        PIL Image with legend
    """
    num_colors = len(pattern.legend)
    if num_colors == 0:
        return Image.new("RGB", (100, 50), (255, 255, 255))

    cols = 2
    rows = (num_colors + cols - 1) // cols

    width = cell_width * cols
    height = row_height * rows + 40  # +40 for header

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font = get_font(12)
    small_font = get_font(10)

    # Draw header
    draw.text((10, 10), "Color Legend", fill=(0, 0, 0), font=font)
    draw.line([(10, 30), (width - 10, 30)], fill=(200, 200, 200))

    # Draw legend entries
    for i, entry in enumerate(pattern.legend):
        col = i % cols
        row = i // cols

        x = col * cell_width + 10
        y = row * row_height + 40

        # Color swatch
        swatch_size = 18
        draw.rectangle(
            [x, y + 2, x + swatch_size, y + swatch_size + 2],
            fill=entry.dmc_color.rgb,
            outline=(0, 0, 0)
        )

        # Symbol
        draw.text((x + swatch_size + 5, y + 2), entry.symbol, fill=(0, 0, 0), font=font)

        # DMC code and name
        text = f"DMC {entry.dmc_color.code}"
        draw.text((x + swatch_size + 25, y + 2), text, fill=(0, 0, 0), font=small_font)

        # Stitch count
        if entry.stitch_count > 0:
            count_text = f"({entry.stitch_count})"
            draw.text((x + swatch_size + 25, y + 14), count_text, fill=(100, 100, 100), font=small_font)

    return img


def render_comparison(
    original: Image.Image,
    pixelated: Image.Image,
    pattern: Pattern,
    cell_size: int = 10
) -> Image.Image:
    """Create side-by-side comparison of original, pixelated, and pattern.

    Args:
        original: Original input image
        pixelated: Pixelated version
        pattern: Final pattern
        cell_size: Cell size for pattern preview

    Returns:
        Combined PIL Image showing all three stages
    """
    # Render pattern preview
    pattern_preview = render_color_preview(pattern, cell_size)

    # Resize all to same height
    target_height = max(original.height, pixelated.height, pattern_preview.height)
    target_height = min(target_height, 400)  # Cap at 400px

    def resize_to_height(img: Image.Image, height: int) -> Image.Image:
        aspect = img.width / img.height
        new_width = int(height * aspect)
        return img.resize((new_width, height), Image.Resampling.LANCZOS)

    orig_resized = resize_to_height(original, target_height)
    pix_resized = resize_to_height(pixelated, target_height)
    pattern_resized = resize_to_height(pattern_preview, target_height)

    # Create combined image
    padding = 20
    total_width = orig_resized.width + pix_resized.width + pattern_resized.width + padding * 4
    total_height = target_height + 60  # Extra space for labels

    combined = Image.new("RGB", (total_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(combined)
    font = get_font(12)

    # Paste images
    x = padding
    combined.paste(orig_resized, (x, 40))
    draw.text((x, 10), "Original", fill=(0, 0, 0), font=font)

    x += orig_resized.width + padding
    combined.paste(pix_resized, (x, 40))
    draw.text((x, 10), "Pixelated", fill=(0, 0, 0), font=font)

    x += pix_resized.width + padding
    combined.paste(pattern_resized, (x, 40))
    draw.text((x, 10), "Pattern Preview", fill=(0, 0, 0), font=font)

    return combined


def create_pattern_sheet(
    pattern: Pattern,
    show_grid_numbers: bool = True
) -> Image.Image:
    """Create a complete pattern sheet with grid and legend.

    Args:
        pattern: The Pattern object
        show_grid_numbers: Whether to show row/column numbers

    Returns:
        PIL Image with complete pattern sheet
    """
    # Determine cell size based on pattern dimensions
    if max(pattern.metadata.width, pattern.metadata.height) > 100:
        cell_size = 15
    elif max(pattern.metadata.width, pattern.metadata.height) > 60:
        cell_size = 20
    else:
        cell_size = 25

    # Render components
    symbol_grid = render_symbol_grid(pattern, cell_size)
    legend = render_legend(pattern)

    # Calculate total size
    margin = 40
    number_margin = 30 if show_grid_numbers else 0

    total_width = symbol_grid.width + legend.width + margin * 3 + number_margin
    total_height = max(symbol_grid.height, legend.height) + margin * 2 + number_margin + 60

    # Create combined image
    sheet = Image.new("RGB", (total_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    font = get_font(14)
    small_font = get_font(10)

    # Title
    title = pattern.metadata.title or "Cross-Stitch Pattern"
    draw.text((margin, 20), title, fill=(0, 0, 0), font=font)

    # Metadata
    meta_text = f"{pattern.metadata.width}×{pattern.metadata.height} stitches | {pattern.metadata.color_count} colors | {pattern.metadata.difficulty.capitalize()}"
    draw.text((margin, 40), meta_text, fill=(100, 100, 100), font=small_font)

    # Paste symbol grid
    grid_x = margin + number_margin
    grid_y = 70 + number_margin
    sheet.paste(symbol_grid, (grid_x, grid_y))

    # Draw row/column numbers if requested
    if show_grid_numbers:
        for i in range(0, pattern.metadata.width, 10):
            x = grid_x + i * cell_size + cell_size // 2
            draw.text((x - 5, grid_y - 15), str(i + 1), fill=(100, 100, 100), font=small_font)

        for i in range(0, pattern.metadata.height, 10):
            y = grid_y + i * cell_size + cell_size // 2
            draw.text((margin, y - 5), str(i + 1), fill=(100, 100, 100), font=small_font)

    # Paste legend
    legend_x = grid_x + symbol_grid.width + margin
    legend_y = 70
    sheet.paste(legend, (legend_x, legend_y))

    return sheet
