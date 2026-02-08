"""Image pixelation and color quantization for cross-stitch patterns."""

from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
from typing import Optional


def resize_to_grid(
    img: Image.Image,
    width: int,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
    resample_method: str = "lanczos"
) -> Image.Image:
    """Resize image to target grid dimensions.

    Args:
        img: Input PIL Image
        width: Target width in stitches
        height: Target height in stitches (calculated from aspect ratio if None)
        maintain_aspect: If True, maintain original aspect ratio
        resample_method: "lanczos" (smooth, for photos) or "nearest" (pixel-perfect)

    Returns:
        Resized PIL Image
    """
    if height is None or maintain_aspect:
        aspect = img.height / img.width
        height = int(width * aspect)

    # LANCZOS: smooth anti-aliased downscaling (good for photos, introduces new colors)
    # NEAREST: pixel-perfect (good for pre-designed pixel art, preserves exact colors)
    if resample_method == "nearest":
        resampler = Image.Resampling.NEAREST
    else:
        resampler = Image.Resampling.LANCZOS

    resized = img.resize((width, height), resampler)
    return resized


def extract_unique_colors(img: Image.Image) -> tuple[Image.Image, np.ndarray]:
    """Extract unique colors from an image without quantization.

    For pre-designed cross-stitch images that already have a limited palette.
    Returns the image unchanged along with its actual color palette.

    Args:
        img: Input PIL Image (RGB)

    Returns:
        Tuple of (original image, palette array of unique colors)
    """
    arr = np.array(img)
    pixels = arr.reshape(-1, 3)

    # Find unique colors
    unique_colors = np.unique(pixels, axis=0)

    return img, unique_colors.astype(np.uint8)


def quantize_colors_kmeans(
    img: Image.Image,
    n_colors: int,
    random_state: int = 42
) -> tuple[Image.Image, np.ndarray]:
    """Reduce image to N colors using K-means clustering.

    Args:
        img: Input PIL Image (RGB)
        n_colors: Target number of colors
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (quantized image, palette array of shape (n_colors, 3))
    """
    # Convert to numpy array and reshape for clustering
    arr = np.array(img)
    h, w = arr.shape[:2]
    pixels = arr.reshape(-1, 3).astype(np.float32)

    # Run K-means clustering
    kmeans = KMeans(
        n_clusters=n_colors,
        random_state=random_state,
        n_init=10,
        max_iter=300
    )
    labels = kmeans.fit_predict(pixels)
    palette = kmeans.cluster_centers_.astype(np.uint8)

    # Reconstruct image with quantized colors
    quantized_pixels = palette[labels]
    quantized_arr = quantized_pixels.reshape(h, w, 3)
    quantized_img = Image.fromarray(quantized_arr)

    return quantized_img, palette


def quantize_colors_median_cut(
    img: Image.Image,
    n_colors: int
) -> tuple[Image.Image, np.ndarray]:
    """Reduce image to N colors using PIL's median cut algorithm.

    This is faster than K-means but may produce slightly different results.

    Args:
        img: Input PIL Image (RGB)
        n_colors: Target number of colors

    Returns:
        Tuple of (quantized image, palette array)
    """
    # Use PIL's built-in quantization
    quantized = img.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)

    # Get palette
    palette_data = quantized.getpalette()[:n_colors * 3]
    palette = np.array(palette_data, dtype=np.uint8).reshape(-1, 3)

    # Convert back to RGB
    quantized_rgb = quantized.convert("RGB")

    return quantized_rgb, palette


def apply_dithering(
    img: Image.Image,
    n_colors: int,
    dither: bool = True
) -> Image.Image:
    """Apply Floyd-Steinberg dithering during quantization.

    Dithering can help maintain gradients in the pattern but
    may make it more complex to stitch.

    Args:
        img: Input PIL Image (RGB)
        n_colors: Target number of colors
        dither: If True, apply dithering; if False, use flat colors

    Returns:
        Quantized PIL Image
    """
    dither_method = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE

    # Convert to palette mode with dithering
    quantized = img.quantize(
        colors=n_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=dither_method
    )

    return quantized.convert("RGB")


def pixelate(
    img: Image.Image,
    grid_width: int,
    grid_height: Optional[int] = None,
    n_colors: int = 8,
    use_dithering: bool = False,
    quantize_method: str = "kmeans"
) -> tuple[Image.Image, np.ndarray]:
    """Complete pixelation pipeline: resize + quantize.

    Args:
        img: Input PIL Image
        grid_width: Target width in stitches
        grid_height: Target height (or None for auto aspect ratio)
        n_colors: Number of colors to reduce to
        use_dithering: Apply dithering for smoother gradients
        quantize_method: "kmeans" or "median_cut"

    Returns:
        Tuple of (pixelated image, color palette array)
    """
    # Step 1: Resize to grid dimensions
    resized = resize_to_grid(img, grid_width, grid_height)

    # Step 2: Quantize colors
    if use_dithering:
        pixelated = apply_dithering(resized, n_colors, dither=True)
        # Extract palette from dithered image
        arr = np.array(pixelated)
        unique_colors = np.unique(arr.reshape(-1, 3), axis=0)
        palette = unique_colors[:n_colors]
    elif quantize_method == "kmeans":
        pixelated, palette = quantize_colors_kmeans(resized, n_colors)
    else:
        pixelated, palette = quantize_colors_median_cut(resized, n_colors)

    return pixelated, palette


def pixelate_predesigned(
    img: Image.Image,
    grid_width: Optional[int] = None,
    grid_height: Optional[int] = None,
    max_colors: Optional[int] = None,
    merge_threshold: int = 30
) -> tuple[Image.Image, np.ndarray, dict]:
    """Process a pre-designed cross-stitch image.

    For images that are already designed for cross-stitch (limited colors,
    clean edges). Uses NEAREST neighbor resize to preserve pixel boundaries
    and extracts existing colors rather than quantizing.

    Args:
        img: Input PIL Image (already designed for cross-stitch)
        grid_width: Target width in stitches (None = use original width)
        grid_height: Target height (None = auto aspect ratio)
        max_colors: If set, merge similar colors to reduce palette
        merge_threshold: Color distance threshold for merging (0-255)

    Returns:
        Tuple of (processed image, color palette, info dict)
    """
    info = {
        "original_size": (img.width, img.height),
        "resize_method": None,
        "colors_before_merge": 0,
        "colors_after_merge": 0,
        "merged_colors": 0,
    }

    # Step 1: Resize if needed (using NEAREST to preserve pixels)
    if grid_width is not None and grid_width != img.width:
        resized = resize_to_grid(img, grid_width, grid_height, resample_method="nearest")
        info["resize_method"] = "NEAREST (pixel-perfect)"
        info["resized_to"] = (resized.width, resized.height)
    else:
        resized = img
        info["resize_method"] = "none (original size)"
        info["resized_to"] = (img.width, img.height)

    # Step 2: Extract existing unique colors
    processed, palette = extract_unique_colors(resized)
    info["colors_before_merge"] = len(palette)

    # Step 3: Optionally merge similar colors
    if max_colors is not None and len(palette) > max_colors:
        indices = get_color_indices(processed, palette)
        palette, indices = merge_similar_colors(palette, indices, threshold=merge_threshold)

        # Reconstruct image with merged palette
        h, w = indices.shape
        merged_pixels = palette[indices.flatten()].reshape(h, w, 3)
        processed = Image.fromarray(merged_pixels.astype(np.uint8))

        info["colors_after_merge"] = len(palette)
        info["merged_colors"] = info["colors_before_merge"] - len(palette)
    else:
        info["colors_after_merge"] = len(palette)
        info["merged_colors"] = 0

    return processed, palette, info


def snap_to_dominant_colors(
    img: Image.Image,
    n_colors: int
) -> tuple[Image.Image, np.ndarray, dict]:
    """Snap all pixels to the N most dominant colors in the image.

    For pre-designed cross-stitch images that have anti-aliasing artifacts.
    Identifies the N most common colors by pixel count, then snaps every
    pixel to its nearest dominant color.

    Args:
        img: Input PIL Image
        n_colors: Number of dominant colors to keep

    Returns:
        Tuple of (cleaned image, palette of dominant colors, info dict)
    """
    arr = np.array(img)
    h, w = arr.shape[:2]
    pixels = arr.reshape(-1, 3)

    # Find unique colors and their counts
    unique_colors, inverse, counts = np.unique(
        pixels, axis=0, return_inverse=True, return_counts=True
    )

    info = {
        "original_colors": len(unique_colors),
        "dominant_colors": min(n_colors, len(unique_colors)),
        "pixels_snapped": 0,
    }

    if len(unique_colors) <= n_colors:
        # Already at or below target, no snapping needed
        return img, unique_colors.astype(np.uint8), info

    # Find the N most common colors
    dominant_indices = np.argsort(counts)[::-1][:n_colors]
    dominant_colors = unique_colors[dominant_indices]

    # For each pixel, find nearest dominant color
    new_pixels = np.zeros_like(pixels)
    pixels_changed = 0

    for i, pixel in enumerate(pixels):
        original_color_idx = inverse[i]

        if original_color_idx in dominant_indices:
            # This pixel is already a dominant color
            new_pixels[i] = pixel
        else:
            # Snap to nearest dominant color
            distances = np.sum((dominant_colors.astype(np.int32) - pixel.astype(np.int32)) ** 2, axis=1)
            nearest_idx = np.argmin(distances)
            new_pixels[i] = dominant_colors[nearest_idx]
            pixels_changed += 1

    info["pixels_snapped"] = pixels_changed

    # Reconstruct image
    new_arr = new_pixels.reshape(h, w, 3)
    new_img = Image.fromarray(new_arr.astype(np.uint8))

    return new_img, dominant_colors.astype(np.uint8), info


def multi_step_resize(
    img: Image.Image,
    grid_width: int,
    grid_height: Optional[int] = None,
    num_steps: int = 3,
    mode: str = "majority",
    return_intermediates: bool = False
) -> Image.Image | tuple[Image.Image, list[Image.Image], dict]:
    """Resize in multiple steps to better preserve details.

    Large single-step resizes lose too much information. By doing multiple
    smaller reductions, we preserve more detail at each step.

    Example with 3 steps from 1024 to 50:
      1024 → 369 → 134 → 50  (each step ~2.7× reduction)

    vs single step:
      1024 → 50  (20× reduction, lots of detail lost)

    Args:
        img: Input PIL Image (should be quantized first)
        grid_width: Final target width
        grid_height: Final target height (None = maintain aspect ratio)
        num_steps: Number of resize steps (1-5, default 3)
        mode: Resize mode for all steps (default "majority")
        return_intermediates: If True, return (final, [intermediates], info_dict)

    Returns:
        If return_intermediates is False: Resized PIL Image
        If return_intermediates is True: (final_image, list_of_intermediates, info_dict)
    """
    src_w, src_h = img.size

    if grid_height is None:
        aspect = src_h / src_w
        grid_height = int(grid_width * aspect)

    # Clamp num_steps
    num_steps = max(1, min(5, num_steps))

    # If source is already small enough, just do one step
    if src_w <= grid_width * 2 or num_steps == 1:
        final = boundary_preserving_resize(img, grid_width, grid_height, mode=mode)
        if return_intermediates:
            return final, [], {"num_steps": 1, "mode": mode, "sizes": [(grid_width, grid_height)]}
        return final

    # Calculate intermediate sizes using geometric progression
    # We want: src_w → size1 → size2 → ... → grid_width
    # Each step has the same reduction ratio
    ratio = (src_w / grid_width) ** (1.0 / num_steps)

    sizes = []
    for i in range(1, num_steps + 1):
        step_width = int(src_w / (ratio ** i))
        step_height = int(src_h / (ratio ** i))
        # Ensure we don't go below target
        step_width = max(step_width, grid_width)
        step_height = max(step_height, grid_height)
        sizes.append((step_width, step_height))

    # Ensure final size is exact
    sizes[-1] = (grid_width, grid_height)

    # Remove duplicate sizes (can happen with small reductions)
    unique_sizes = []
    prev_size = (src_w, src_h)
    for size in sizes:
        if size != prev_size:
            unique_sizes.append(size)
            prev_size = size
    sizes = unique_sizes if unique_sizes else [(grid_width, grid_height)]

    # Perform resize steps
    current = img
    intermediates = []

    for i, (w, h) in enumerate(sizes):
        current = boundary_preserving_resize(current, w, h, mode=mode)
        if i < len(sizes) - 1:  # Don't include final in intermediates
            intermediates.append(current)

    if return_intermediates:
        info = {
            "num_steps": len(sizes),
            "mode": mode,
            "sizes": sizes,
            "reduction_per_step": ratio,
        }
        return current, intermediates, info

    return current


def two_step_resize(
    img: Image.Image,
    grid_width: int,
    grid_height: Optional[int] = None,
    intermediate_scale: float = 2.5,
    step1_mode: str = "majority",
    step2_mode: str = "majority",
    return_intermediate: bool = False
) -> Image.Image | tuple[Image.Image, Image.Image, dict]:
    """Resize in two steps (legacy function, use multi_step_resize instead)."""
    # Delegate to multi_step_resize for backwards compatibility
    if return_intermediate:
        final, intermediates, info = multi_step_resize(
            img, grid_width, grid_height,
            num_steps=2, mode=step1_mode,
            return_intermediates=True
        )
        intermediate = intermediates[0] if intermediates else None
        return final, intermediate, info
    return multi_step_resize(img, grid_width, grid_height, num_steps=2, mode=step1_mode)


def boundary_preserving_resize(
    img: Image.Image,
    grid_width: int,
    grid_height: Optional[int] = None,
    mode: str = "majority"
) -> Image.Image:
    """Resize image using majority voting.

    For each output pixel, examines the corresponding block in the source
    and picks the most common color. Uses padding (not cropping) to ensure
    the entire image is preserved.

    Args:
        img: Input PIL Image (should be quantized first for best results)
        grid_width: Target width
        grid_height: Target height (None = maintain aspect ratio)
        mode: "majority" (picks most common color per block)

    Returns:
        Resized PIL Image
    """
    from scipy import stats
    import math

    arr = np.array(img)
    src_h, src_w = arr.shape[:2]

    if grid_height is None:
        aspect = src_h / src_w
        grid_height = int(grid_width * aspect)

    # Calculate block sizes using ceiling to cover entire image
    block_h = math.ceil(src_h / grid_height)
    block_w = math.ceil(src_w / grid_width)

    # Calculate padded size
    padded_h = block_h * grid_height
    padded_w = block_w * grid_width

    # Detect background color (most common color on edges) for padding
    edges = np.concatenate([
        arr[0, :].reshape(-1, 3),      # top edge
        arr[-1, :].reshape(-1, 3),     # bottom edge
        arr[:, 0].reshape(-1, 3),      # left edge
        arr[:, -1].reshape(-1, 3),     # right edge
    ])
    # Find most common edge color
    edge_ints = edges[:, 0].astype(np.int32) * 65536 + edges[:, 1].astype(np.int32) * 256 + edges[:, 2].astype(np.int32)
    unique_vals, counts = np.unique(edge_ints, return_counts=True)
    bg_int = unique_vals[np.argmax(counts)]

    # Convert to RGB integers
    arr_int = arr[:, :, 0].astype(np.int32) * 65536 + arr[:, :, 1].astype(np.int32) * 256 + arr[:, :, 2].astype(np.int32)

    # Pad image with background color (centered)
    if padded_h > src_h or padded_w > src_w:
        pad_top = (padded_h - src_h) // 2
        pad_left = (padded_w - src_w) // 2
        arr_padded = np.full((padded_h, padded_w), bg_int, dtype=np.int32)
        arr_padded[pad_top:pad_top + src_h, pad_left:pad_left + src_w] = arr_int
        arr_int = arr_padded

    # For efficiency, use regular block sizes when possible
    if block_h > 0 and block_w > 0:
        # Reshape into blocks: (grid_height, block_h, grid_width, block_w)
        blocks = arr_int.reshape(grid_height, block_h, grid_width, block_w)
        # Transpose to (grid_height, grid_width, block_h, block_w)
        blocks = blocks.transpose(0, 2, 1, 3)
        # Flatten each block: (grid_height, grid_width, block_h * block_w)
        blocks = blocks.reshape(grid_height, grid_width, -1)

        # Find mode (most common value) for each block
        # Use scipy.stats.mode for efficiency
        result_int, _ = stats.mode(blocks, axis=2, keepdims=False)
        result_int = result_int.astype(np.int32)
    else:
        # Fallback for very small reductions - use loop method
        block_w_f = src_w / grid_width
        block_h_f = src_h / grid_height
        result_int = np.zeros((grid_height, grid_width), dtype=np.int32)

        for out_y in range(grid_height):
            src_y1 = int(out_y * block_h_f)
            src_y2 = min(max(int((out_y + 1) * block_h_f), src_y1 + 1), src_h)
            for out_x in range(grid_width):
                src_x1 = int(out_x * block_w_f)
                src_x2 = min(max(int((out_x + 1) * block_w_f), src_x1 + 1), src_w)
                block = arr_int[src_y1:src_y2, src_x1:src_x2].ravel()
                unique_vals, counts = np.unique(block, return_counts=True)
                result_int[out_y, out_x] = unique_vals[np.argmax(counts)]

    # Unpack integers back to RGB
    result = np.zeros((grid_height, grid_width, 3), dtype=np.uint8)
    result[:, :, 0] = (result_int >> 16) & 0xFF
    result[:, :, 1] = (result_int >> 8) & 0xFF
    result[:, :, 2] = result_int & 0xFF

    return Image.fromarray(result)


def quantize_then_resize(
    img: Image.Image,
    grid_width: int,
    n_colors: int,
    grid_height: Optional[int] = None,
    preserve_boundaries: bool = False,
    boundary_mode: str = "minority"
) -> tuple[Image.Image, np.ndarray, dict]:
    """Quantize colors at full resolution, THEN resize.

    This is the correct approach for AI-generated cross-stitch images that
    need to be resized. By quantizing first, we establish clean color boundaries
    before downsampling, which preserves the structure.

    Pipeline: Full-res K-means → Resize (NEAREST or boundary-preserving)

    Args:
        img: Input PIL Image (high resolution AI-generated image)
        grid_width: Target width in stitches
        n_colors: Number of colors to reduce to
        grid_height: Target height (None = maintain aspect ratio)
        preserve_boundaries: Use boundary-preserving resize instead of NEAREST
        boundary_mode: Mode for boundary preservation ("minority", "darkest", "contrast")

    Returns:
        Tuple of (resized image, color palette, info dict)
    """
    from sklearn.cluster import KMeans

    arr = np.array(img)
    h, w = arr.shape[:2]
    pixels = arr.reshape(-1, 3).astype(np.float32)

    resize_method = f"boundary-preserving ({boundary_mode})" if preserve_boundaries else "NEAREST"
    info = {
        "original_size": (w, h),
        "original_colors": len(np.unique(pixels.astype(np.uint8), axis=0)),
        "method": f"K-means at full resolution, then {resize_method} resize",
    }

    # Step 1: K-means clustering at full resolution
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    labels = kmeans.fit_predict(pixels)
    palette = kmeans.cluster_centers_.astype(np.uint8)

    # Reconstruct clean image at full resolution
    clean_pixels = palette[labels]
    clean_arr = clean_pixels.reshape(h, w, 3)
    clean_img = Image.fromarray(clean_arr)

    info["colors_after_quantize"] = n_colors

    # Step 2: Resize
    if preserve_boundaries:
        resized = boundary_preserving_resize(
            clean_img, grid_width, grid_height, mode=boundary_mode
        )
        info["boundary_mode"] = boundary_mode
    else:
        resized = resize_to_grid(clean_img, grid_width, grid_height, resample_method="nearest")

    info["final_size"] = (resized.width, resized.height)
    info["final_colors"] = len(np.unique(np.array(resized).reshape(-1, 3), axis=0))

    return resized, palette, info


def get_color_indices(
    img: Image.Image,
    palette: np.ndarray
) -> np.ndarray:
    """Convert image to grid of color indices.

    Args:
        img: Quantized PIL Image
        palette: Color palette array (n_colors, 3)

    Returns:
        2D numpy array of color indices
    """
    arr = np.array(img)
    h, w = arr.shape[:2]

    # Vectorized: reshape to (h*w, 3) and compute distances to all palette colors
    pixels = arr.reshape(-1, 3).astype(np.int32)
    palette_int = palette.astype(np.int32)

    # Compute squared distances using broadcasting: (n_pixels, 1, 3) - (1, n_colors, 3)
    # Result: (n_pixels, n_colors)
    diff = pixels[:, np.newaxis, :] - palette_int[np.newaxis, :, :]
    distances = np.sum(diff ** 2, axis=2)

    # Find index of minimum distance for each pixel
    indices_flat = np.argmin(distances, axis=1)

    return indices_flat.reshape(h, w).astype(np.int32)


def merge_similar_colors(
    palette: np.ndarray,
    indices: np.ndarray,
    threshold: int = 30
) -> tuple[np.ndarray, np.ndarray]:
    """Merge similar colors in palette to reduce complexity.

    Args:
        palette: Color palette array (n_colors, 3)
        indices: 2D array of color indices
        threshold: Maximum color distance to merge (Euclidean in RGB)

    Returns:
        Tuple of (new palette, remapped indices)
    """
    n_colors = len(palette)
    merged_to = list(range(n_colors))  # Track which color each merges to

    # Find pairs of similar colors
    for i in range(n_colors):
        if merged_to[i] != i:
            continue  # Already merged

        for j in range(i + 1, n_colors):
            if merged_to[j] != j:
                continue  # Already merged

            # Calculate Euclidean distance
            dist = np.sqrt(np.sum((palette[i].astype(np.float32) - palette[j].astype(np.float32)) ** 2))

            if dist < threshold:
                # Merge j into i (keep the one with more pixels)
                count_i = np.sum(indices == i)
                count_j = np.sum(indices == j)

                if count_j > count_i:
                    merged_to[i] = j
                else:
                    merged_to[j] = i

    # Build new palette and remap indices
    unique_targets = sorted(set(merged_to))
    new_palette = palette[unique_targets]

    # Create mapping from old index to new index
    old_to_new = {old: unique_targets.index(merged_to[old]) for old in range(n_colors)}

    # Remap indices
    new_indices = np.vectorize(lambda x: old_to_new[x])(indices)

    return new_palette, new_indices
