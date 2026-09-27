"""Image loading and validation for cross-stitch pattern generation."""

from pathlib import Path
from PIL import Image
import numpy as np


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
