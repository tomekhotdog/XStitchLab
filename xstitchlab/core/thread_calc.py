"""Thread estimation calculations for cross-stitch patterns."""

from dataclasses import dataclass
from typing import Optional
import math

from .pattern import Pattern


# Standard DMC skein length in meters
DMC_SKEIN_LENGTH_METERS = 8.0

# Thread length per stitch based on fabric count (in cm)
# These are approximate values for full cross stitches using 2 strands
THREAD_PER_STITCH_CM = {
    14: 2.5,   # 14-count Aida
    16: 2.2,   # 16-count Aida
    18: 2.0,   # 18-count Aida
    11: 3.0,   # 11-count Aida
    22: 1.8,   # 22-count hardanger
}


@dataclass
class ThreadEstimate:
    """Thread estimate for a single color."""
    dmc_code: str
    dmc_name: str
    stitch_count: int
    thread_length_cm: float
    thread_length_meters: float
    skeins_needed: int
    skeins_decimal: float


class ThreadCalculator:
    """Calculate thread requirements for cross-stitch patterns."""

    def __init__(
        self,
        fabric_count: int = 14,
        strands: int = 2,
        wastage_factor: float = 0.2,
        stitch_type: str = "full_cross"
    ):
        """Initialize calculator.

        Args:
            fabric_count: Aida fabric count (14, 16, 18, etc.)
            strands: Number of strands to use (typically 2)
            wastage_factor: Additional thread for starts/stops (0.1-0.3)
            stitch_type: Type of stitch ("full_cross", "half", "backstitch")
        """
        self.fabric_count = fabric_count
        self.strands = strands
        self.wastage_factor = wastage_factor
        self.stitch_type = stitch_type

        # Get base thread per stitch
        self.thread_per_stitch_cm = THREAD_PER_STITCH_CM.get(
            fabric_count,
            2.5  # Default for unknown counts
        )

        # Adjust for stitch type
        if stitch_type == "half":
            self.thread_per_stitch_cm *= 0.6
        elif stitch_type == "backstitch":
            self.thread_per_stitch_cm *= 0.4

        # Adjust for strand count (standard is 2)
        self.thread_per_stitch_cm *= strands / 2

    def calculate_thread_length(self, stitch_count: int) -> tuple[float, float]:
        """Calculate thread length for given stitch count.

        Args:
            stitch_count: Number of stitches

        Returns:
            Tuple of (length in cm, length in meters)
        """
        base_length_cm = stitch_count * self.thread_per_stitch_cm
        with_wastage_cm = base_length_cm * (1 + self.wastage_factor)

        return with_wastage_cm, with_wastage_cm / 100

    def calculate_skeins(self, length_meters: float) -> tuple[int, float]:
        """Calculate skeins needed for given thread length.

        Args:
            length_meters: Thread length in meters

        Returns:
            Tuple of (whole skeins needed, decimal skeins)
        """
        skeins_decimal = length_meters / DMC_SKEIN_LENGTH_METERS
        skeins_whole = math.ceil(skeins_decimal)

        return skeins_whole, skeins_decimal

    def estimate_color(
        self,
        dmc_code: str,
        dmc_name: str,
        stitch_count: int
    ) -> ThreadEstimate:
        """Estimate thread for a single color.

        Args:
            dmc_code: DMC color code
            dmc_name: DMC color name
            stitch_count: Number of stitches in this color

        Returns:
            ThreadEstimate with all calculations
        """
        length_cm, length_m = self.calculate_thread_length(stitch_count)
        skeins_whole, skeins_decimal = self.calculate_skeins(length_m)

        return ThreadEstimate(
            dmc_code=dmc_code,
            dmc_name=dmc_name,
            stitch_count=stitch_count,
            thread_length_cm=length_cm,
            thread_length_meters=length_m,
            skeins_needed=skeins_whole,
            skeins_decimal=skeins_decimal
        )

    def estimate_pattern(self, pattern: Pattern) -> list[ThreadEstimate]:
        """Estimate thread for entire pattern.

        Args:
            pattern: Pattern to estimate

        Returns:
            List of ThreadEstimate for each color
        """
        estimates = []

        for entry in pattern.legend:
            if entry.stitch_count > 0:
                est = self.estimate_color(
                    dmc_code=entry.dmc_color.code,
                    dmc_name=entry.dmc_color.name,
                    stitch_count=entry.stitch_count
                )
                estimates.append(est)

        # Sort by stitch count descending
        estimates.sort(key=lambda e: e.stitch_count, reverse=True)

        return estimates

    def estimate_all(self, pattern: Pattern) -> list[dict]:
        """Estimate thread for pattern, returning dict format.

        Args:
            pattern: Pattern to estimate

        Returns:
            List of estimate dictionaries
        """
        estimates = self.estimate_pattern(pattern)

        return [
            {
                "dmc_code": e.dmc_code,
                "name": e.dmc_name,
                "stitch_count": e.stitch_count,
                "meters": round(e.thread_length_meters, 2),
                "skeins": e.skeins_needed,
                "skeins_decimal": round(e.skeins_decimal, 2)
            }
            for e in estimates
        ]

    def get_shopping_list(self, pattern: Pattern) -> str:
        """Generate a text shopping list.

        Args:
            pattern: Pattern to generate list for

        Returns:
            Formatted shopping list string
        """
        estimates = self.estimate_pattern(pattern)

        lines = [
            f"Thread Shopping List for: {pattern.metadata.title}",
            f"Pattern Size: {pattern.metadata.width}×{pattern.metadata.height} stitches",
            f"Fabric: {self.fabric_count}-count Aida",
            f"Strands: {self.strands}",
            "",
            "DMC Code | Name | Stitches | Meters | Skeins",
            "-" * 60,
        ]

        total_skeins = 0
        total_meters = 0

        for est in estimates:
            lines.append(
                f"{est.dmc_code:8} | {est.dmc_name[:20]:20} | {est.stitch_count:6,} | "
                f"{est.thread_length_meters:5.1f}m | {est.skeins_needed}"
            )
            total_skeins += est.skeins_needed
            total_meters += est.thread_length_meters

        lines.extend([
            "-" * 60,
            f"TOTAL: {total_skeins} skeins ({total_meters:.1f} meters)",
        ])

        return "\n".join(lines)

    def export_shopping_list(
        self,
        pattern: Pattern,
        output_path: str,
        format: str = "txt"
    ) -> None:
        """Export shopping list to file.

        Args:
            pattern: Pattern to export
            output_path: File path for output
            format: Output format ("txt" or "json")
        """
        import json
        from pathlib import Path

        path = Path(output_path)

        if format == "json":
            data = {
                "pattern_title": pattern.metadata.title,
                "pattern_size": f"{pattern.metadata.width}×{pattern.metadata.height}",
                "fabric_count": self.fabric_count,
                "strands": self.strands,
                "threads": self.estimate_all(pattern)
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        else:
            with open(path, "w") as f:
                f.write(self.get_shopping_list(pattern))


def quick_estimate(
    pattern: Pattern,
    fabric_count: int = 14
) -> dict:
    """Quick thread estimate summary.

    Args:
        pattern: Pattern to estimate
        fabric_count: Aida fabric count

    Returns:
        Summary dict with totals
    """
    calc = ThreadCalculator(fabric_count=fabric_count)
    estimates = calc.estimate_pattern(pattern)

    total_skeins = sum(e.skeins_needed for e in estimates)
    total_meters = sum(e.thread_length_meters for e in estimates)

    return {
        "color_count": len(estimates),
        "total_stitches": pattern.metadata.total_stitches,
        "total_skeins": total_skeins,
        "total_meters": round(total_meters, 1),
        "fabric_count": fabric_count,
        "fabric_size_inches": (
            pattern.metadata.fabric_width_inches,
            pattern.metadata.fabric_height_inches
        )
    }
