"""Image loading and validation for cross-stitch pattern generation."""

from pathlib import Path
from PIL import Image
import numpy as np
from typing import Optional


SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class ImageLoadError(Exception):
    """Raised when image loading fails."""
    pass


def validate_image_path(path: Path | str) -> Path:
    """Validate that the image path exists and is a supported format."""
    path = Path(path)

    if not path.exists():
        raise ImageLoadError(f"Image file not found: {path}")

    if not path.is_file():
        raise ImageLoadError(f"Path is not a file: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ImageLoadError(
            f"Unsupported image format: {path.suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    return path


def load_image(path: Path | str) -> Image.Image:
    """Load an image from file and convert to RGB."""
    path = validate_image_path(path)

    try:
        img = Image.open(path)

        # Convert to RGB (handles RGBA, palette, grayscale, etc.)
        if img.mode != "RGB":
            # Handle transparency by compositing on white background
            if img.mode == "RGBA" or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert("RGB")

        return img

    except Exception as e:
        raise ImageLoadError(f"Failed to load image: {e}")


def load_image_as_array(path: Path | str) -> np.ndarray:
    """Load an image and return as numpy array (H, W, 3)."""
    img = load_image(path)
    return np.array(img)


def get_image_info(path: Path | str) -> dict:
    """Get information about an image file."""
    path = validate_image_path(path)

    with Image.open(path) as img:
        return {
            "path": str(path),
            "filename": path.name,
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0,
        }


def resize_for_preview(
    img: Image.Image,
    max_size: int = 800
) -> Image.Image:
    """Resize image for preview, maintaining aspect ratio."""
    if max(img.width, img.height) <= max_size:
        return img.copy()

    if img.width > img.height:
        new_width = max_size
        new_height = int(img.height * (max_size / img.width))
    else:
        new_height = max_size
        new_width = int(img.width * (max_size / img.height))

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def preprocess_image(
    img: Image.Image,
    enhance_edges: bool = False,
    remove_background: bool = False
) -> Image.Image:
    """Apply optional preprocessing to improve pattern quality."""
    result = img.copy()

    if enhance_edges:
        from PIL import ImageFilter
        # Apply subtle edge enhancement
        result = result.filter(ImageFilter.EDGE_ENHANCE)

    if remove_background:
        # Simple background removal: assume corners represent background
        # This is a basic implementation - for better results, use rembg library
        arr = np.array(result)
        # Get corner colors (average of 5x5 corners)
        corners = [
            arr[:5, :5].mean(axis=(0, 1)),
            arr[:5, -5:].mean(axis=(0, 1)),
            arr[-5:, :5].mean(axis=(0, 1)),
            arr[-5:, -5:].mean(axis=(0, 1)),
        ]
        # Use most common corner color as background
        bg_color = np.mean(corners, axis=0).astype(np.uint8)

        # Replace similar colors with white (threshold of 30)
        diff = np.abs(arr.astype(np.float32) - bg_color.astype(np.float32))
        mask = diff.sum(axis=2) < 90  # threshold
        arr[mask] = [255, 255, 255]
        result = Image.fromarray(arr)

    return result


def create_thumbnail(
    img: Image.Image,
    size: tuple[int, int] = (150, 150)
) -> Image.Image:
    """Create a square thumbnail of the image."""
    thumb = img.copy()
    thumb.thumbnail(size, Image.Resampling.LANCZOS)
    return thumb
