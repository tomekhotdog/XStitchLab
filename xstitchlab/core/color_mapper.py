"""Map RGB colors to DMC thread colors with perceptual accuracy."""

import numpy as np
from typing import Optional

# Fix for colormath compatibility with numpy 2.x
# numpy.asscalar was removed in numpy 2.0
if not hasattr(np, 'asscalar'):
    np.asscalar = lambda a: a.item()

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

from .pattern import DMCColor, DMCPalette


def rgb_to_lab(rgb: tuple[int, int, int]) -> LabColor:
    """Convert RGB (0-255) to CIELAB color space."""
    srgb = sRGBColor(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    return convert_color(srgb, LabColor)


def color_distance_rgb(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int]
) -> float:
    """Calculate Euclidean distance in RGB space."""
    # Use int to avoid uint8 overflow
    return np.sqrt(sum((int(a) - int(b)) ** 2 for a, b in zip(c1, c2)))


def color_distance_lab(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int]
) -> float:
    """Calculate perceptual color distance using CIEDE2000 in LAB space.

    This is more accurate for human perception than RGB distance.
    """
    lab1 = rgb_to_lab(c1)
    lab2 = rgb_to_lab(c2)

    # Handle numpy array deprecation in colormath
    # by converting to scalar if needed
    delta = delta_e_cie2000(lab1, lab2)
    if hasattr(delta, 'item'):
        delta = delta.item()
    return float(delta)


def find_nearest_dmc_rgb(
    rgb: tuple[int, int, int],
    palette: DMCPalette
) -> DMCColor:
    """Find nearest DMC color using RGB Euclidean distance."""
    best_match = None
    best_distance = float("inf")

    for dmc_color in palette:
        dist = color_distance_rgb(rgb, dmc_color.rgb)
        if dist < best_distance:
            best_distance = dist
            best_match = dmc_color

    return best_match


def find_nearest_dmc_lab(
    rgb: tuple[int, int, int],
    palette: DMCPalette,
    _cache: Optional[dict] = None
) -> DMCColor:
    """Find nearest DMC color using CIEDE2000 perceptual distance.

    This provides better color matching for human perception but is slower.
    Results are cached for performance.
    """
    if _cache is None:
        _cache = {}

    cache_key = rgb
    if cache_key in _cache:
        return _cache[cache_key]

    best_match = None
    best_distance = float("inf")

    for dmc_color in palette:
        dist = color_distance_lab(rgb, dmc_color.rgb)
        if dist < best_distance:
            best_distance = dist
            best_match = dmc_color

    _cache[cache_key] = best_match
    return best_match


class ColorMapper:
    """Maps image colors to DMC thread colors."""

    def __init__(
        self,
        palette: Optional[DMCPalette] = None,
        use_lab: bool = True
    ):
        """Initialize the color mapper.

        Args:
            palette: DMC palette to use (loads default if None)
            use_lab: Use CIELAB color space for perceptual matching
        """
        self.palette = palette or DMCPalette()
        self.use_lab = use_lab
        self._cache: dict[tuple[int, int, int], DMCColor] = {}

        # Pre-compute LAB values for DMC colors as numpy array for vectorized ops
        if use_lab:
            self._dmc_list = list(self.palette)  # For indexed lookup
            lab_values = []
            for dmc in self._dmc_list:
                lab = rgb_to_lab(dmc.rgb)
                lab_values.append([lab.lab_l, lab.lab_a, lab.lab_b])
            self._dmc_lab_array = np.array(lab_values, dtype=np.float64)

    def find_nearest(self, rgb: tuple[int, int, int]) -> DMCColor:
        """Find nearest DMC color for given RGB value."""
        if rgb in self._cache:
            return self._cache[rgb]

        if self.use_lab:
            result = self._find_nearest_lab(rgb)
        else:
            result = find_nearest_dmc_rgb(rgb, self.palette)

        self._cache[rgb] = result
        return result

    def _find_nearest_lab(self, rgb: tuple[int, int, int]) -> DMCColor:
        """Find nearest DMC using vectorized LAB Euclidean distance (Delta E 76).

        Uses numpy vectorized operations for fast nearest-neighbor lookup.
        Delta E 76 (Euclidean LAB distance) is much faster than CIEDE2000
        while still providing perceptually-based color matching.
        """
        input_lab = rgb_to_lab(rgb)
        input_lab_arr = np.array([input_lab.lab_l, input_lab.lab_a, input_lab.lab_b])

        # Vectorized Euclidean distance in LAB space
        distances = np.sqrt(np.sum((self._dmc_lab_array - input_lab_arr) ** 2, axis=1))
        best_idx = np.argmin(distances)

        return self._dmc_list[best_idx]

    def map_palette(
        self,
        colors: np.ndarray
    ) -> list[DMCColor]:
        """Map an array of RGB colors to DMC colors.

        Args:
            colors: Array of shape (n_colors, 3) with RGB values

        Returns:
            List of DMCColor objects
        """
        return [self.find_nearest(tuple(c)) for c in colors]

    def map_image(
        self,
        img_array: np.ndarray
    ) -> tuple[np.ndarray, list[DMCColor]]:
        """Map all pixels in image to DMC colors.

        Args:
            img_array: Image array of shape (H, W, 3)

        Returns:
            Tuple of (mapped image array, list of unique DMC colors used)
        """
        h, w = img_array.shape[:2]
        result = np.zeros_like(img_array)

        # Get unique colors first for efficiency
        unique_colors = np.unique(img_array.reshape(-1, 3), axis=0)

        # Map unique colors to DMC
        color_map: dict[tuple, DMCColor] = {}
        for color in unique_colors:
            rgb = tuple(color)
            dmc = self.find_nearest(rgb)
            color_map[rgb] = dmc

        # Apply mapping to all pixels
        for i in range(h):
            for j in range(w):
                rgb = tuple(img_array[i, j])
                dmc = color_map[rgb]
                result[i, j] = dmc.rgb

        return result, list(set(color_map.values()))

    def reduce_to_max_colors(
        self,
        dmc_colors: list[DMCColor],
        max_colors: int,
        stitch_counts: Optional[dict[str, int]] = None
    ) -> list[DMCColor]:
        """Reduce palette to maximum number of colors.

        Keeps the most frequently used colors and merges others
        into their nearest neighbors.

        Args:
            dmc_colors: List of DMC colors to reduce
            max_colors: Maximum number of colors to keep
            stitch_counts: Optional dict mapping DMC code to stitch count

        Returns:
            Reduced list of DMC colors
        """
        if len(dmc_colors) <= max_colors:
            return dmc_colors

        # Sort by stitch count if available, otherwise keep original order
        if stitch_counts:
            sorted_colors = sorted(
                dmc_colors,
                key=lambda c: stitch_counts.get(c.code, 0),
                reverse=True
            )
        else:
            sorted_colors = dmc_colors

        # Keep top N colors
        return sorted_colors[:max_colors]

    def get_substitutes(
        self,
        dmc_color: DMCColor,
        n_alternatives: int = 3
    ) -> list[tuple[DMCColor, float]]:
        """Get alternative DMC colors similar to the given color.

        Args:
            dmc_color: The DMC color to find alternatives for
            n_alternatives: Number of alternatives to return

        Returns:
            List of (DMCColor, distance) tuples sorted by similarity
        """
        distances: list[tuple[DMCColor, float]] = []

        for dmc in self.palette:
            if dmc.code == dmc_color.code:
                continue

            if self.use_lab:
                dist = color_distance_lab(dmc_color.rgb, dmc.rgb)
            else:
                dist = color_distance_rgb(dmc_color.rgb, dmc.rgb)

            distances.append((dmc, dist))

        distances.sort(key=lambda x: x[1])
        return distances[:n_alternatives]

    def clear_cache(self) -> None:
        """Clear the color mapping cache."""
        self._cache.clear()
