"""Pattern data structures for cross-stitch patterns."""

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass(frozen=True)
class DMCColor:
    """Represents a DMC thread color."""
    code: str
    name: str
    rgb: tuple[int, int, int]

    def to_hex(self) -> str:
        """Convert RGB to hex color string."""
        return f"#{self.rgb[0]:02x}{self.rgb[1]:02x}{self.rgb[2]:02x}"

    @classmethod
    def from_dict(cls, data: dict) -> "DMCColor":
        """Create DMCColor from dictionary."""
        return cls(
            code=data["code"],
            name=data["name"],
            rgb=tuple(data["rgb"])
        )


@dataclass
class ColorLegendEntry:
    """Entry in the pattern color legend."""
    dmc_color: DMCColor
    symbol: str
    stitch_count: int = 0


@dataclass
class PatternMetadata:
    """Metadata for a cross-stitch pattern."""
    title: str = "Untitled Pattern"
    width: int = 0  # in stitches
    height: int = 0  # in stitches
    color_count: int = 0
    total_stitches: int = 0
    difficulty: str = "medium"  # easy, medium, hard
    fabric_count: int = 14  # standard Aida count
    source_image: Optional[str] = None

    @property
    def fabric_width_inches(self) -> float:
        """Calculate fabric width in inches for the given fabric count."""
        return self.width / self.fabric_count + 2  # +2 for margins

    @property
    def fabric_height_inches(self) -> float:
        """Calculate fabric height in inches for the given fabric count."""
        return self.height / self.fabric_count + 2  # +2 for margins

    def get_difficulty_rating(self) -> str:
        """Determine difficulty based on color count and size."""
        total = self.total_stitches
        colors = self.color_count

        if colors <= 5 and total <= 1600:
            return "easy"
        elif colors <= 10 and total <= 4000:
            return "medium"
        else:
            return "hard"


@dataclass
class Pattern:
    """Complete cross-stitch pattern with grid, legend, and metadata."""
    grid: list[list[int]]  # 2D grid of color indices
    legend: list[ColorLegendEntry] = field(default_factory=list)
    metadata: PatternMetadata = field(default_factory=PatternMetadata)

    # Standard symbols for pattern display (up to ~50 unique symbols)
    SYMBOLS: list[str] = field(default_factory=lambda: [
        "●", "■", "▲", "◆", "★", "♦", "♣", "♠", "♥", "○",
        "□", "△", "◇", "☆", "◐", "◑", "◒", "◓", "⬟", "⬡",
        "⊕", "⊗", "⊙", "⊚", "⊛", "⊜", "⊝", "⧫", "⬢", "⬣",
        "▼", "◀", "▶", "▷", "◁", "⬤", "⬥", "⬦", "⬧", "⬨",
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"
    ])

    def __post_init__(self):
        """Initialize metadata after creation."""
        if self.grid:
            self.metadata.height = len(self.grid)
            self.metadata.width = len(self.grid[0]) if self.grid else 0
            self.metadata.color_count = len(self.legend)
            self.metadata.total_stitches = sum(
                entry.stitch_count for entry in self.legend
            )
            self.metadata.difficulty = self.metadata.get_difficulty_rating()

    def get_symbol(self, color_index: int) -> str:
        """Get symbol for a color index."""
        if 0 <= color_index < len(self.SYMBOLS):
            return self.SYMBOLS[color_index]
        return str(color_index)

    def get_color_at(self, x: int, y: int) -> Optional[DMCColor]:
        """Get DMC color at grid position."""
        if 0 <= y < len(self.grid) and 0 <= x < len(self.grid[0]):
            color_idx = self.grid[y][x]
            if 0 <= color_idx < len(self.legend):
                return self.legend[color_idx].dmc_color
        return None

    def count_stitches(self) -> dict[str, int]:
        """Count stitches per color, updating legend entries and metadata.

        The background color (lightest/white) is excluded from total_stitches
        since it's typically left unstitched in cross-stitch patterns.
        """
        counts: dict[int, int] = {}
        for row in self.grid:
            for color_idx in row:
                counts[color_idx] = counts.get(color_idx, 0) + 1

        for idx, entry in enumerate(self.legend):
            entry.stitch_count = counts.get(idx, 0)

        # Find background color: prefer pure white, then fall back to lightest
        # Background is left unstitched, so exclude from total
        background_idx = None
        for idx, entry in enumerate(self.legend):
            if entry.dmc_color.rgb == (255, 255, 255):
                background_idx = idx
                break
        if background_idx is None:
            max_brightness = -1
            for idx, entry in enumerate(self.legend):
                r, g, b = entry.dmc_color.rgb
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                if brightness > max_brightness:
                    max_brightness = brightness
                    background_idx = idx

        # Update metadata - exclude background from stitch count
        self.metadata.total_stitches = sum(
            entry.stitch_count for idx, entry in enumerate(self.legend)
            if idx != background_idx
        )
        self.metadata.color_count = len(self.legend)
        self.metadata.difficulty = self.metadata.get_difficulty_rating()

        return {
            self.legend[idx].dmc_color.code: count
            for idx, count in counts.items()
            if idx < len(self.legend)
        }

    def to_dict(self) -> dict:
        """Convert pattern to dictionary for JSON export."""
        return {
            "metadata": {
                "title": self.metadata.title,
                "width": self.metadata.width,
                "height": self.metadata.height,
                "color_count": self.metadata.color_count,
                "total_stitches": self.metadata.total_stitches,
                "difficulty": self.metadata.difficulty,
                "fabric_count": self.metadata.fabric_count,
                "fabric_width_inches": round(self.metadata.fabric_width_inches, 1),
                "fabric_height_inches": round(self.metadata.fabric_height_inches, 1),
                "source_image": self.metadata.source_image
            },
            "legend": [
                {
                    "symbol": entry.symbol,
                    "dmc_code": entry.dmc_color.code,
                    "dmc_name": entry.dmc_color.name,
                    "rgb": list(entry.dmc_color.rgb),
                    "stitch_count": entry.stitch_count
                }
                for entry in self.legend
            ],
            "grid": self.grid
        }

    def to_json(self, path: Path | str) -> None:
        """Export pattern to JSON file."""
        path = Path(path)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        """Create Pattern from dictionary."""
        metadata = PatternMetadata(
            title=data["metadata"].get("title", "Untitled"),
            width=data["metadata"]["width"],
            height=data["metadata"]["height"],
            color_count=data["metadata"]["color_count"],
            total_stitches=data["metadata"]["total_stitches"],
            difficulty=data["metadata"]["difficulty"],
            fabric_count=data["metadata"].get("fabric_count", 14),
            source_image=data["metadata"].get("source_image")
        )

        # Build legend first so __post_init__ sees the correct values
        legend = []
        for entry_data in data["legend"]:
            dmc_color = DMCColor(
                code=entry_data["dmc_code"],
                name=entry_data["dmc_name"],
                rgb=tuple(entry_data["rgb"])
            )
            legend.append(ColorLegendEntry(
                dmc_color=dmc_color,
                symbol=entry_data["symbol"],
                stitch_count=entry_data["stitch_count"]
            ))

        return cls(grid=data["grid"], legend=legend, metadata=metadata)

    @classmethod
    def from_json(cls, path: Path | str) -> "Pattern":
        """Load pattern from JSON file."""
        path = Path(path)
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)


class DMCPalette:
    """DMC color palette manager."""

    def __init__(self, data_path: Optional[Path | str] = None):
        """Load DMC colors from JSON file."""
        if data_path is None:
            # Default to package data directory
            data_path = Path(__file__).parent.parent.parent / "data" / "dmc_colors.json"

        self.data_path = Path(data_path)
        self.colors: list[DMCColor] = []
        self._load_colors()

    def _load_colors(self) -> None:
        """Load colors from JSON file."""
        with open(self.data_path) as f:
            data = json.load(f)

        self.colors = [
            DMCColor.from_dict(c) for c in data["colors"]
        ]

    def get_by_code(self, code: str) -> Optional[DMCColor]:
        """Find DMC color by code."""
        for color in self.colors:
            if color.code == code:
                return color
        return None

    def get_all_rgb(self) -> list[tuple[int, int, int]]:
        """Get all RGB values as a list."""
        return [c.rgb for c in self.colors]

    def __len__(self) -> int:
        return len(self.colors)

    def __iter__(self):
        return iter(self.colors)
