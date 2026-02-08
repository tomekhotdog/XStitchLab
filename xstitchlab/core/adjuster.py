"""XStitchLabs pattern adjustment for cleaner, more stitchable patterns.

This module provides post-quantization spatial cleanup to produce patterns
with cohesive color blocks, straight edges, and minimal noise.
"""

import numpy as np
from PIL import Image
from typing import Optional
from dataclasses import dataclass
from scipy import ndimage


@dataclass
class AdjustmentSettings:
    """Settings for pattern adjustment."""

    # === Cleanup operations ===
    # Isolated pixel removal - removes stray single pixels
    remove_isolated: bool = True

    # Small region absorption - can remove thin lines
    min_region_size: int = 1  # 1 = disabled, >1 absorbs small regions

    # Majority vote smoothing - removes minority boundary pixels
    smoothing_iterations: int = 0  # 0 = disabled

    # Edge straightening - aggressive, changes diagonal boundaries
    straighten_edges: bool = False

    # === Helpful operations (on by default) ===
    # Fill internal holes - fill stray pixels inside solid regions
    fill_holes: bool = True

    # Snap diagonals to stair-steps - easier to stitch
    snap_diagonals: bool = True

    # Connect broken boundary lines - bridge 1px gaps
    connect_lines: bool = True

    # Rectangularize - prefer rectangular shapes (good for architecture)
    rectangularize: bool = True

    # === Regularity enforcement ===
    # Regularize repeated rectangular elements (windows, doors)
    regularize_rectangles: bool = False
    min_rectangle_group_size: int = 3  # Min similar rectangles to form a group

    # Enforce pattern repetition (make near-duplicate columns identical)
    enforce_repetition: bool = False
    repetition_similarity_threshold: float = 0.8  # Min similarity to consider duplicate

    @property
    def description(self) -> str:
        """Human-readable description of current settings."""
        parts = []
        if self.fill_holes:
            parts.append("fill holes")
        if self.snap_diagonals:
            parts.append("snap diagonals")
        if self.connect_lines:
            parts.append("connect lines")
        if self.remove_isolated:
            parts.append("remove isolated")
        if self.min_region_size > 1:
            parts.append(f"absorb <{self.min_region_size}px")
        if self.smoothing_iterations > 0:
            parts.append(f"{self.smoothing_iterations}x smoothing")
        if self.straighten_edges:
            parts.append("straighten edges")
        if self.rectangularize:
            parts.append("rectangularize")
        if self.regularize_rectangles:
            parts.append("regularize rectangles")
        if self.enforce_repetition:
            parts.append(f"enforce repetition (>{self.repetition_similarity_threshold:.0%})")
        return ", ".join(parts) if parts else "no adjustments"


def remove_isolated_pixels(indices: np.ndarray) -> np.ndarray:
    """Remove isolated single pixels that differ from all cardinal neighbors.

    A pixel is isolated if none of its 4 cardinal neighbors (up, down, left, right)
    share its color. Such pixels are replaced with the most common neighbor color.

    Args:
        indices: 2D array of color indices

    Returns:
        Adjusted indices array with isolated pixels removed
    """
    result = indices.copy()
    h, w = indices.shape

    for i in range(h):
        for j in range(w):
            current = indices[i, j]

            # Get cardinal neighbors
            neighbors = []
            if i > 0:
                neighbors.append(indices[i-1, j])
            if i < h - 1:
                neighbors.append(indices[i+1, j])
            if j > 0:
                neighbors.append(indices[i, j-1])
            if j < w - 1:
                neighbors.append(indices[i, j+1])

            # Check if isolated (no neighbor shares our color)
            if len(neighbors) > 0 and current not in neighbors:
                # Replace with most common neighbor
                from collections import Counter
                most_common = Counter(neighbors).most_common(1)[0][0]
                result[i, j] = most_common

    return result


def absorb_small_regions(
    indices: np.ndarray,
    min_size: int = 4
) -> np.ndarray:
    """Absorb small connected regions into surrounding dominant color.

    Uses connected component analysis to find regions smaller than min_size,
    then replaces them with the most common neighboring color.

    Args:
        indices: 2D array of color indices
        min_size: Minimum region size to keep (smaller regions get absorbed)

    Returns:
        Adjusted indices array with small regions absorbed
    """
    if min_size <= 1:
        return indices

    result = indices.copy()
    n_colors = int(indices.max()) + 1

    # Process each color separately
    for color_idx in range(n_colors):
        # Create binary mask for this color
        mask = (indices == color_idx)

        # Label connected components
        labeled, num_features = ndimage.label(mask)

        if num_features == 0:
            continue

        # Find small regions
        for region_id in range(1, num_features + 1):
            region_mask = (labeled == region_id)
            region_size = np.sum(region_mask)

            if region_size < min_size:
                # Find boundary pixels and their external neighbors
                # Dilate the region and subtract to get boundary
                dilated = ndimage.binary_dilation(region_mask)
                boundary_exterior = dilated & ~region_mask

                # Get colors of exterior boundary pixels
                exterior_colors = result[boundary_exterior]

                if len(exterior_colors) > 0:
                    # Replace region with most common exterior color
                    from collections import Counter
                    # Filter out the current color from consideration
                    exterior_colors = exterior_colors[exterior_colors != color_idx]
                    if len(exterior_colors) > 0:
                        replacement = Counter(exterior_colors).most_common(1)[0][0]
                        result[region_mask] = replacement

    return result


def majority_vote_filter(
    indices: np.ndarray,
    iterations: int = 1
) -> np.ndarray:
    """Apply majority vote filter to smooth color regions.

    For each pixel, examines its 3x3 neighborhood. If the pixel's color
    is a minority (appears <= 2 times in the 9-pixel window), it's replaced
    with the majority color.

    Args:
        indices: 2D array of color indices
        iterations: Number of filter passes

    Returns:
        Smoothed indices array
    """
    result = indices.copy()
    h, w = indices.shape

    for _ in range(iterations):
        new_result = result.copy()

        for i in range(h):
            for j in range(w):
                # Get 3x3 neighborhood
                i_min, i_max = max(0, i-1), min(h, i+2)
                j_min, j_max = max(0, j-1), min(w, j+2)

                neighborhood = result[i_min:i_max, j_min:j_max].flatten()
                current = result[i, j]

                # Count occurrences
                from collections import Counter
                counts = Counter(neighborhood)
                current_count = counts[current]

                # If minority (2 or fewer in up to 9 pixels), replace with majority
                if current_count <= 2 and len(neighborhood) > 3:
                    majority = counts.most_common(1)[0][0]
                    new_result[i, j] = majority

        result = new_result

    return result


def straighten_edges(indices: np.ndarray) -> np.ndarray:
    """Straighten edges between color regions.

    Detects boundary pixels and adjusts them to prefer horizontal/vertical
    edges over diagonal ones. This is a more aggressive adjustment.

    Args:
        indices: 2D array of color indices

    Returns:
        Adjusted indices array with straighter edges
    """
    result = indices.copy()
    h, w = indices.shape

    # Find boundary pixels (pixels with at least one different neighbor)
    for i in range(1, h-1):
        for j in range(1, w-1):
            current = result[i, j]

            # Get 4-connected neighbors
            neighbors_4 = [
                result[i-1, j],  # up
                result[i+1, j],  # down
                result[i, j-1],  # left
                result[i, j+1],  # right
            ]

            # Get diagonal neighbors
            diagonals = [
                result[i-1, j-1],  # top-left
                result[i-1, j+1],  # top-right
                result[i+1, j-1],  # bottom-left
                result[i+1, j+1],  # bottom-right
            ]

            # Check if this is a boundary pixel
            if current in neighbors_4:
                continue  # Has at least one same-color cardinal neighbor, probably fine

            # This pixel differs from all cardinal neighbors - it's likely noise
            # or a diagonal boundary. Check if making it match a cardinal neighbor
            # would create a straighter edge.

            from collections import Counter

            # Count how many cardinals match each color
            cardinal_counts = Counter(neighbors_4)

            # If there's a clear majority among cardinals, adopt that color
            most_common_cardinal, count = cardinal_counts.most_common(1)[0]
            if count >= 2:
                result[i, j] = most_common_cardinal

    return result


def fill_internal_holes(indices: np.ndarray) -> np.ndarray:
    """Fill stray pixels that are inside solid regions.

    Unlike remove_isolated_pixels (which removes ANY isolated pixel),
    this only fills pixels that are clearly inside a region - surrounded
    by a single color on at least 3 sides. Boundary pixels are preserved.

    Args:
        indices: 2D array of color indices

    Returns:
        Adjusted indices array with internal holes filled
    """
    result = indices.copy()
    h, w = indices.shape

    for i in range(h):
        for j in range(w):
            current = indices[i, j]

            # Get cardinal neighbors
            neighbors = []
            if i > 0:
                neighbors.append(indices[i-1, j])
            if i < h - 1:
                neighbors.append(indices[i+1, j])
            if j > 0:
                neighbors.append(indices[i, j-1])
            if j < w - 1:
                neighbors.append(indices[i, j+1])

            if len(neighbors) < 3:
                continue

            # Count neighbor colors
            from collections import Counter
            counts = Counter(neighbors)

            # If 3+ neighbors are the SAME color and it's different from current,
            # this is likely an internal hole, not a boundary
            most_common_color, most_common_count = counts.most_common(1)[0]
            if most_common_count >= 3 and most_common_color != current:
                result[i, j] = most_common_color

    return result


def snap_diagonals_to_stairs(indices: np.ndarray) -> np.ndarray:
    """Convert diagonal boundaries to stair-step patterns.

    Diagonals in cross-stitch are stitched as stair-steps anyway,
    so this makes the pattern clearer and easier to follow.

    Looks for 2x2 diagonal patterns (checkerboard) and converts to stairs:
        A B      A A      A B      A B
        B A  ->  B B  or  B A  ->  A B

    The choice between horizontal and vertical stairs is based on
    which direction has more color support from neighbors.

    Args:
        indices: 2D array of color indices

    Returns:
        Adjusted indices array with stair-stepped diagonals
    """
    # Work on original to avoid cascading changes
    original = indices.copy()
    result = indices.copy()
    h, w = indices.shape

    # Collect changes first
    changes = []

    # Scan for 2x2 diagonal patterns
    for i in range(h - 1):
        for j in range(w - 1):
            # Get 2x2 block from ORIGINAL
            tl = original[i, j]      # top-left
            tr = original[i, j+1]    # top-right
            bl = original[i+1, j]    # bottom-left
            br = original[i+1, j+1]  # bottom-right

            # Check for diagonal pattern: TL==BR and TR==BL and TL!=TR
            # This is a checkerboard pattern with two colors
            if not (tl == br and tr == bl and tl != tr):
                continue

            # This is a diagonal - decide how to convert to stairs
            # Count support for horizontal vs vertical stair orientation

            horizontal_support = 0  # Support for making rows uniform
            vertical_support = 0    # Support for making columns uniform

            # Check neighbors above - do they match top row colors?
            if i > 0:
                if original[i-1, j] == tl:
                    horizontal_support += 1  # top-left column continues up
                if original[i-1, j+1] == tl:
                    horizontal_support += 1  # extending tl color right makes sense
                if original[i-1, j] == tl and original[i-1, j+1] == tr:
                    vertical_support += 1  # above row has same pattern

            # Check neighbors below - do they match bottom row colors?
            if i + 2 < h:
                if original[i+2, j] == bl:
                    horizontal_support += 1
                if original[i+2, j+1] == bl:
                    horizontal_support += 1
                if original[i+2, j] == bl and original[i+2, j+1] == br:
                    vertical_support += 1

            # Check neighbors left - do they match left column colors?
            if j > 0:
                if original[i, j-1] == tl:
                    vertical_support += 1  # left continues the tl color
                if original[i+1, j-1] == tl:
                    vertical_support += 1  # extending tl color down makes sense
                if original[i, j-1] == tl and original[i+1, j-1] == bl:
                    horizontal_support += 1

            # Check neighbors right - do they match right column colors?
            if j + 2 < w:
                if original[i, j+2] == tr:
                    vertical_support += 1
                if original[i+1, j+2] == tr:
                    vertical_support += 1
                if original[i, j+2] == tr and original[i+1, j+2] == br:
                    horizontal_support += 1

            # Convert to stairs based on support
            if horizontal_support >= vertical_support:
                # Make horizontal stair: top row = tl color, bottom row = bl color
                # A B -> A A
                # B A    B B
                changes.append((i, j+1, tl))      # tr becomes tl
                changes.append((i+1, j+1, bl))    # br becomes bl
            else:
                # Make vertical stair: left col = tl color, right col = tr color
                # A B -> A B
                # B A    A B
                changes.append((i+1, j, tl))      # bl becomes tl
                changes.append((i+1, j+1, tr))    # br becomes tr

    # Apply all changes
    for i, j, new_color in changes:
        result[i, j] = new_color

    return result


def connect_broken_lines(indices: np.ndarray) -> np.ndarray:
    """Bridge 1-pixel gaps in boundary lines.

    Looks for patterns where a boundary line has a single-pixel gap
    and fills it to create a continuous line.

    Pattern detected (and similar rotations):
        A B A      A A A
        B B B  ->  B B B

    Args:
        indices: 2D array of color indices

    Returns:
        Adjusted indices array with connected boundary lines
    """
    result = indices.copy()
    h, w = indices.shape

    # Horizontal gap detection
    for i in range(h):
        for j in range(1, w - 1):
            left = result[i, j-1]
            center = result[i, j]
            right = result[i, j+1]

            # Gap pattern: same color on both sides, different in middle
            if left == right and left != center:
                # Check if this is a boundary line (has different color above or below)
                is_boundary = False
                if i > 0 and result[i-1, j] != center:
                    is_boundary = True
                if i < h - 1 and result[i+1, j] != center:
                    is_boundary = True

                # Only fill if it's connecting a boundary line
                if is_boundary:
                    # Check that filling wouldn't break an intentional feature
                    # by verifying the center pixel is truly isolated in this context
                    neighbors_same = 0
                    if i > 0 and result[i-1, j] == center:
                        neighbors_same += 1
                    if i < h - 1 and result[i+1, j] == center:
                        neighbors_same += 1

                    # Only fill if center has no vertical support
                    if neighbors_same == 0:
                        result[i, j] = left

    # Vertical gap detection
    for i in range(1, h - 1):
        for j in range(w):
            top = result[i-1, j]
            center = result[i, j]
            bottom = result[i+1, j]

            if top == bottom and top != center:
                is_boundary = False
                if j > 0 and result[i, j-1] != center:
                    is_boundary = True
                if j < w - 1 and result[i, j+1] != center:
                    is_boundary = True

                if is_boundary:
                    neighbors_same = 0
                    if j > 0 and result[i, j-1] == center:
                        neighbors_same += 1
                    if j < w - 1 and result[i, j+1] == center:
                        neighbors_same += 1

                    if neighbors_same == 0:
                        result[i, j] = top

    return result


def rectangularize(indices: np.ndarray) -> np.ndarray:
    """Prefer rectangular shapes by completing corners conservatively.

    Useful for architectural patterns (doors, windows, walls) where clean
    rectangles are desirable. This is a CONSERVATIVE operation that only
    fills in corners where the outlier pixel is clearly isolated.

    Works by completing 2x2 corners: If 3 of 4 pixels in a 2x2 block match,
    AND the outlier pixel has no other same-color neighbors outside the block,
    fill the 4th to create a clean corner.

    Args:
        indices: 2D array of color indices

    Returns:
        Adjusted indices array with cleaner rectangular corners
    """
    # Work on original indices to avoid cascading changes
    original = indices.copy()
    result = indices.copy()
    h, w = indices.shape

    # Collect all changes first, then apply (prevents cascading)
    changes = []

    # Complete 2x2 corners conservatively
    for i in range(h - 1):
        for j in range(w - 1):
            # Get 2x2 block from ORIGINAL
            block = [
                original[i, j],      # top-left (pos 0)
                original[i, j+1],    # top-right (pos 1)
                original[i+1, j],    # bottom-left (pos 2)
                original[i+1, j+1],  # bottom-right (pos 3)
            ]

            from collections import Counter
            counts = Counter(block)

            # Check if exactly 3 match (one outlier)
            if len(counts) != 2:
                continue

            most_common, mc_count = counts.most_common(1)[0]
            if mc_count != 3:
                continue

            # Find the outlier position
            outlier_pos = None
            outlier_color = None
            for idx, color in enumerate(block):
                if color != most_common:
                    outlier_pos = idx
                    outlier_color = color
                    break

            if outlier_pos is None:
                continue

            # Get the outlier's coordinates
            positions = [(i, j), (i, j+1), (i+1, j), (i+1, j+1)]
            oi, oj = positions[outlier_pos]

            # Check if outlier has any same-color neighbors OUTSIDE the 2x2 block
            # If it does, it's part of a larger region and we shouldn't change it
            has_external_support = False

            # Check all 4 cardinal neighbors of the outlier
            for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ni, nj = oi + di, oj + dj
                if ni < 0 or ni >= h or nj < 0 or nj >= w:
                    continue
                # Skip if this neighbor is inside the 2x2 block
                if (ni, nj) in positions:
                    continue
                # Check if neighbor has same color as outlier
                if original[ni, nj] == outlier_color:
                    has_external_support = True
                    break

            # Only fill if the outlier is truly isolated (no external support)
            if not has_external_support:
                changes.append((oi, oj, most_common))

    # Apply all changes
    for i, j, new_color in changes:
        result[i, j] = new_color

    return result


def regularize_rectangles(
    indices: np.ndarray,
    min_group_size: int = 3
) -> np.ndarray:
    """Regularize repeated rectangular elements to consistent sizes.

    Detects rectangular regions (windows, doors), groups similar-sized ones,
    and normalizes them to consistent dimensions. This helps recover uniform
    window sizes that were distorted during downsampling.

    Args:
        indices: 2D array of color indices
        min_group_size: Minimum similar rectangles to form a group

    Returns:
        Adjusted indices array with regularized rectangles
    """
    from collections import defaultdict

    result = indices.copy()
    h, w = indices.shape
    n_colors = int(indices.max()) + 1

    # Find all rectangular regions
    all_rectangles = []

    for color_idx in range(n_colors):
        mask = (indices == color_idx)
        labeled, num_features = ndimage.label(mask)

        for region_id in range(1, num_features + 1):
            region_mask = (labeled == region_id)
            region_size = np.sum(region_mask)

            if region_size < 4:  # Too small to be a meaningful rectangle
                continue

            # Find bounding box
            ys, xs = np.where(region_mask)
            min_x, max_x = xs.min(), xs.max()
            min_y, max_y = ys.min(), ys.max()
            rect_width = max_x - min_x + 1
            rect_height = max_y - min_y + 1
            bbox_area = rect_width * rect_height

            # Calculate rectangularity
            rectangularity = region_size / bbox_area

            # Only consider sufficiently rectangular regions
            if rectangularity < 0.8:
                continue

            all_rectangles.append({
                'color': color_idx,
                'min_x': min_x, 'max_x': max_x,
                'min_y': min_y, 'max_y': max_y,
                'width': rect_width,
                'height': rect_height,
                'mask': region_mask
            })

    # Group rectangles by approximate size (within ±1 pixel)
    size_groups = defaultdict(list)
    for rect in all_rectangles:
        # Create a size key that groups similar sizes
        size_key = (rect['width'], rect['height'], rect['color'])
        size_groups[size_key].append(rect)

    # Also check for near-matches (±1 pixel in either dimension)
    merged_groups = []
    used_keys = set()

    for key in size_groups:
        if key in used_keys:
            continue

        w_k, h_k, c_k = key
        group = list(size_groups[key])
        used_keys.add(key)

        # Look for similar size groups to merge
        for other_key in size_groups:
            if other_key in used_keys:
                continue
            w_o, h_o, c_o = other_key
            if c_o != c_k:
                continue
            if abs(w_k - w_o) <= 1 and abs(h_k - h_o) <= 1:
                group.extend(size_groups[other_key])
                used_keys.add(other_key)

        if len(group) >= min_group_size:
            merged_groups.append(group)

    # Normalize each group to median dimensions
    for group in merged_groups:
        # Calculate median dimensions
        widths = [r['width'] for r in group]
        heights = [r['height'] for r in group]
        target_width = int(np.median(widths))
        target_height = int(np.median(heights))

        for rect in group:
            current_width = rect['width']
            current_height = rect['height']

            if current_width == target_width and current_height == target_height:
                continue

            # Adjust rectangle to target size
            # Strategy: expand or contract from center
            center_x = (rect['min_x'] + rect['max_x']) / 2
            center_y = (rect['min_y'] + rect['max_y']) / 2

            new_min_x = int(center_x - target_width / 2 + 0.5)
            new_max_x = new_min_x + target_width - 1
            new_min_y = int(center_y - target_height / 2 + 0.5)
            new_max_y = new_min_y + target_height - 1

            # Clamp to image bounds
            new_min_x = max(0, new_min_x)
            new_max_x = min(w - 1, new_max_x)
            new_min_y = max(0, new_min_y)
            new_max_y = min(h - 1, new_max_y)

            # Clear old rectangle area (set to most common neighbor)
            old_mask = rect['mask']
            # Find most common neighboring color
            dilated = ndimage.binary_dilation(old_mask)
            boundary = dilated & ~old_mask
            if np.any(boundary):
                neighbor_colors = result[boundary]
                from collections import Counter
                bg_color = Counter(neighbor_colors).most_common(1)[0][0]
            else:
                bg_color = 0

            # Clear old area
            result[old_mask] = bg_color

            # Draw new rectangle
            result[new_min_y:new_max_y+1, new_min_x:new_max_x+1] = rect['color']

    return result


def enforce_pattern_repetition(
    indices: np.ndarray,
    similarity_threshold: float = 0.8
) -> np.ndarray:
    """Enforce pattern repetition by making near-duplicate columns identical.

    Detects columns that are nearly identical (suggesting repeated elements
    like windows) and makes them exactly match using majority vote.

    Args:
        indices: 2D array of color indices
        similarity_threshold: Minimum similarity (0-1) to consider columns duplicates

    Returns:
        Adjusted indices array with enforced repetition
    """
    from collections import defaultdict

    result = indices.copy()
    h, w = indices.shape

    # Build column signatures
    columns = [tuple(indices[:, j]) for j in range(w)]

    # Calculate similarity between all column pairs
    def column_similarity(col1, col2):
        matches = sum(1 for a, b in zip(col1, col2) if a == b)
        return matches / len(col1)

    # Group similar columns
    column_groups = []
    assigned = [False] * w

    for i in range(w):
        if assigned[i]:
            continue

        group = [i]
        assigned[i] = True

        for j in range(i + 1, w):
            if assigned[j]:
                continue

            sim = column_similarity(columns[i], columns[j])
            if sim >= similarity_threshold:
                group.append(j)
                assigned[j] = True

        if len(group) >= 2:
            column_groups.append(group)

    # For each group, create canonical column via majority vote and apply
    for group in column_groups:
        # Build canonical column using majority vote at each row
        canonical = []
        for row in range(h):
            row_values = [result[row, col] for col in group]
            from collections import Counter
            majority = Counter(row_values).most_common(1)[0][0]
            canonical.append(majority)

        # Apply canonical column to all columns in group
        for col in group:
            for row in range(h):
                result[row, col] = canonical[row]

    return result


def adjust_pattern(
    indices: np.ndarray,
    palette: np.ndarray,
    settings: Optional[AdjustmentSettings] = None
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Apply XStitchLabs adjustments to a quantized pattern.

    This is the main entry point for pattern adjustment. It applies
    a series of cleanup operations to produce a cleaner, more stitchable
    pattern while preserving the overall design.

    Args:
        indices: 2D array of color indices from pixelation
        palette: Color palette array (n_colors, 3)
        settings: Adjustment settings (uses defaults if None)

    Returns:
        Tuple of (adjusted_indices, adjusted_palette, stats_dict)
        stats_dict contains information about changes made
    """
    if settings is None:
        settings = AdjustmentSettings()

    result = indices.copy()
    stats = {
        "original_unique_positions": {},
        "adjusted_unique_positions": {},
        "pixels_changed": 0,
        "operations_applied": []
    }

    # Count original color distribution
    for color_idx in range(len(palette)):
        stats["original_unique_positions"][color_idx] = int(np.sum(indices == color_idx))

    # === Helpful operations (run first) ===

    # Step 1: Fill internal holes
    if settings.fill_holes:
        before = result.copy()
        result = fill_internal_holes(result)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"fill holes ({changed} pixels)")

    # Step 2: Snap diagonals to stairs
    if settings.snap_diagonals:
        before = result.copy()
        result = snap_diagonals_to_stairs(result)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"snap diagonals ({changed} pixels)")

    # Step 3: Connect broken lines
    if settings.connect_lines:
        before = result.copy()
        result = connect_broken_lines(result)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"connect lines ({changed} pixels)")

    # Step 4: Rectangularize (prefer rectangular shapes)
    if settings.rectangularize:
        before = result.copy()
        result = rectangularize(result)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"rectangularize ({changed} pixels)")

    # === Regularity enforcement ===

    # Step 5: Regularize repeated rectangles (windows, doors)
    if settings.regularize_rectangles:
        before = result.copy()
        result = regularize_rectangles(
            result,
            min_group_size=settings.min_rectangle_group_size
        )
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"regularize rectangles ({changed} pixels)")

    # Step 7: Enforce pattern repetition (make near-duplicate columns identical)
    if settings.enforce_repetition:
        before = result.copy()
        result = enforce_pattern_repetition(
            result,
            similarity_threshold=settings.repetition_similarity_threshold
        )
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"enforce repetition ({changed} pixels)")

    # === Potentially disruptive operations (off by default) ===

    # Step 6: Remove isolated pixels
    if settings.remove_isolated:
        before = result.copy()
        result = remove_isolated_pixels(result)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"remove isolated ({changed} pixels)")

    # Step 5: Absorb small regions
    if settings.min_region_size > 1:
        before = result.copy()
        result = absorb_small_regions(result, settings.min_region_size)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"absorb small regions ({changed} pixels)")

    # Step 6: Majority vote smoothing
    if settings.smoothing_iterations > 0:
        before = result.copy()
        result = majority_vote_filter(result, settings.smoothing_iterations)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"majority smoothing ({changed} pixels)")

    # Step 7: Edge straightening
    if settings.straighten_edges:
        before = result.copy()
        result = straighten_edges(result)
        changed = np.sum(before != result)
        if changed > 0:
            stats["operations_applied"].append(f"straighten edges ({changed} pixels)")

    # Count final color distribution
    for color_idx in range(len(palette)):
        stats["adjusted_unique_positions"][color_idx] = int(np.sum(result == color_idx))

    # Total pixels changed
    stats["pixels_changed"] = int(np.sum(indices != result))

    # Clean up palette - remove colors that are no longer used
    used_colors = np.unique(result)
    if len(used_colors) < len(palette):
        # Remap indices to new palette
        new_palette = palette[used_colors]
        index_map = {old: new for new, old in enumerate(used_colors)}
        result = np.vectorize(lambda x: index_map[x])(result)
        palette = new_palette
        stats["colors_removed"] = len(palette) - len(new_palette)

    return result, palette, stats


def indices_to_image(indices: np.ndarray, palette: np.ndarray) -> Image.Image:
    """Convert color indices back to an RGB image.

    Args:
        indices: 2D array of color indices
        palette: Color palette array (n_colors, 3)

    Returns:
        PIL Image in RGB mode
    """
    h, w = indices.shape
    rgb_array = palette[indices.flatten()].reshape(h, w, 3)
    return Image.fromarray(rgb_array.astype(np.uint8))
