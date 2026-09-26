"""Pattern data structures for cross-stitch patterns."""

from dataclasses import dataclass, field
from typing import Optional
import copy
import json
from pathlib import Path


# Standard symbols for pattern display (up to ~50 unique symbols)
SYMBOLS: list[str] = [
    "●", "■", "▲", "◆", "★", "♦", "♣", "♠", "♥", "○",
    "□", "△", "◇", "☆", "◐", "◑", "◒", "◓", "⬟", "⬡",
    "⊕", "⊗", "⊙", "⊚", "⊛", "⊜", "⊝", "⧫", "⬢", "⬣",
    "▼", "◀", "▶", "▷", "◁", "⬤", "⬥", "⬦", "⬧", "⬨",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"
]


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


@dataclass(frozen=True)
class Segment:
    """Backstitch segment between grid corners (x in 0..width, y in 0..height)."""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def is_unit(self) -> bool:
        """True when the segment spans exactly one cell edge or diagonal."""
        return max(abs(self.x2 - self.x1), abs(self.y2 - self.y1)) == 1

    def to_dict(self) -> dict:
        return {"start": [self.x1, self.y1], "end": [self.x2, self.y2]}

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        """Accept both {"start": [x, y], "end": [x, y]} and {"x1", "y1", "x2", "y2"}."""
        if "start" in d:
            (x1, y1), (x2, y2) = d["start"], d["end"]
            return cls(int(x1), int(y1), int(x2), int(y2))
        return cls(int(d["x1"]), int(d["y1"]), int(d["x2"]), int(d["y2"]))


@dataclass
class OpCall:
    """One step of a recipe: an operation name and its parameters."""
    op: str
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"op": self.op, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: dict) -> "OpCall":
        return cls(op=d["op"], params=dict(d.get("params", {})))


@dataclass
class Pattern:
    """Complete cross-stitch pattern: grid, legend, backstitch, background, recipe.

    Stitch counts and size/total metadata are always derived from the grid;
    values supplied in `metadata` or `legend[*].stitch_count` are overwritten.
    """
    grid: list[list[int]]  # 2D grid of legend indices, grid[y][x]
    legend: list[ColorLegendEntry] = field(default_factory=list)
    metadata: PatternMetadata = field(default_factory=PatternMetadata)
    backstitch: list[Segment] = field(default_factory=list)
    background_index: Optional[int] = None  # legend entry left as bare fabric
    recipe: list[OpCall] = field(default_factory=list)

    # Standard symbols for pattern display (see module-level SYMBOLS)
    SYMBOLS: list[str] = field(default_factory=lambda: list(SYMBOLS))

    def __post_init__(self):
        """Derive stitch counts and metadata from the grid."""
        self.count_stitches()

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        return len(self.grid)

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

    def guess_background_index(self) -> Optional[int]:
        """Legacy heuristic: pure white, else the brightest legend entry."""
        for idx, entry in enumerate(self.legend):
            if tuple(entry.dmc_color.rgb) == (255, 255, 255):
                return idx
        best, best_brightness = None, -1.0
        for idx, entry in enumerate(self.legend):
            r, g, b = entry.dmc_color.rgb
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness > best_brightness:
                best, best_brightness = idx, brightness
        return best

    def count_stitches(self) -> dict[str, int]:
        """Count stitches per color, updating legend entries and metadata.

        The explicit `background_index` (if any) is left unstitched, so it is
        excluded from `total_stitches` but still reported per legend entry.
        """
        counts: dict[int, int] = {}
        for row in self.grid:
            for color_idx in row:
                counts[color_idx] = counts.get(color_idx, 0) + 1

        for idx, entry in enumerate(self.legend):
            entry.stitch_count = counts.get(idx, 0)

        background = self.background_index
        self.metadata.width, self.metadata.height = self.width, self.height
        self.metadata.color_count = len(self.legend)
        self.metadata.total_stitches = sum(
            entry.stitch_count for idx, entry in enumerate(self.legend)
            if idx != background
        )
        self.metadata.difficulty = self.metadata.get_difficulty_rating()

        return {
            self.legend[idx].dmc_color.code: count
            for idx, count in counts.items()
            if idx < len(self.legend)
        }

    def copy(self) -> "Pattern":
        """Deep copy, so operations can transform without mutating the input."""
        return copy.deepcopy(self)

    def to_dict(self) -> dict:
        """Convert pattern to dictionary for JSON export (counts recomputed)."""
        self.count_stitches()
        return {
            "metadata": {
                "title": self.metadata.title,
                "width": self.width,
                "height": self.height,
                "color_count": self.metadata.color_count,
                "total_stitches": self.metadata.total_stitches,
                "difficulty": self.metadata.difficulty,
                "fabric_count": self.metadata.fabric_count,
                "fabric_width_inches": round(self.metadata.fabric_width_inches, 1),
                "fabric_height_inches": round(self.metadata.fabric_height_inches, 1),
                "source_image": self.metadata.source_image,
            },
            "legend": [
                {
                    "symbol": entry.symbol,
                    "dmc_code": entry.dmc_color.code,
                    "dmc_name": entry.dmc_color.name,
                    "rgb": list(entry.dmc_color.rgb),
                    "stitch_count": entry.stitch_count,
                }
                for entry in self.legend
            ],
            "grid": [list(row) for row in self.grid],
            "backstitch": [segment.to_dict() for segment in self.backstitch],
            "background_index": self.background_index,
            "recipe": [call.to_dict() for call in self.recipe],
        }

    def to_json(self, path: Path | str) -> None:
        """Export pattern to JSON file."""
        path = Path(path)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        """Create Pattern from dictionary.

        Lenient with legacy design files: accepts `backstitch_segments` and
        `background_color_index`, ignores stale counts, and falls back to the
        white/brightest heuristic when no background is recorded.
        """
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor(
                    code=str(entry["dmc_code"]),
                    name=entry.get("dmc_name", ""),
                    rgb=tuple(entry["rgb"]),
                ),
                symbol=entry.get("symbol", "?"),
            )
            for entry in data.get("legend", [])
        ]
        meta = data.get("metadata", {})
        metadata = PatternMetadata(
            title=meta.get("title", "Untitled Pattern"),
            fabric_count=int(meta.get("fabric_count", 14)),
            source_image=meta.get("source_image"),
        )
        raw_backstitch = data.get("backstitch") or data.get("backstitch_segments") or []
        backstitch = [Segment.from_dict(s) for s in raw_backstitch]
        background = data.get("background_index", data.get("background_color_index"))
        recipe = [OpCall.from_dict(c) for c in (data.get("recipe") or [])]

        pattern = cls(
            grid=[list(row) for row in data["grid"]],
            legend=legend,
            metadata=metadata,
            backstitch=backstitch,
            background_index=background,
            recipe=recipe,
        )
        if pattern.background_index is None:
            pattern.background_index = pattern.guess_background_index()
            pattern.count_stitches()
        return pattern

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
