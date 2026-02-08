"""Pydantic schemas for pattern data structures."""

from pydantic import BaseModel, Field
from typing import Optional


class DMCColorSchema(BaseModel):
    """DMC thread color."""

    code: str
    name: str
    rgb: tuple[int, int, int]

    @property
    def hex(self) -> str:
        return f"#{self.rgb[0]:02x}{self.rgb[1]:02x}{self.rgb[2]:02x}"


class ColorLegendEntrySchema(BaseModel):
    """Entry in the pattern color legend."""

    symbol: str
    dmc_code: str
    dmc_name: str
    rgb: list[int]
    stitch_count: int = 0


class PatternMetadataSchema(BaseModel):
    """Pattern metadata."""

    title: str = "Untitled Pattern"
    width: int = 0
    height: int = 0
    color_count: int = 0
    total_stitches: int = 0
    difficulty: str = "medium"
    fabric_count: int = 14
    fabric_width_inches: Optional[float] = None
    fabric_height_inches: Optional[float] = None
    source_image: Optional[str] = None


class PatternSchema(BaseModel):
    """Complete cross-stitch pattern."""

    id: str
    metadata: PatternMetadataSchema
    legend: list[ColorLegendEntrySchema]
    grid: list[list[int]]


class PatternCreateRequest(BaseModel):
    """Request to create pattern from image."""

    grid_size: int = Field(default=50, ge=20, le=150, description="Grid width in stitches")
    num_colors: int = Field(default=8, ge=2, le=20, description="Number of colors")
    mode: str = Field(default="photo", description="Processing mode: 'photo' or 'predesigned'")
    dithering: bool = Field(default=False, description="Enable Floyd-Steinberg dithering")
    color_space: str = Field(default="lab", description="Color matching space: 'rgb' or 'lab'")
    fabric_count: int = Field(default=14, description="Fabric count (stitches per inch)")

    # Adjustment settings
    fill_holes: bool = Field(default=True)
    snap_diagonals: bool = Field(default=True)
    connect_lines: bool = Field(default=True)
    remove_isolated: bool = Field(default=False)
    min_region_size: int = Field(default=1)

    # Backstitch settings
    backstitch_enabled: bool = Field(default=False)
    backstitch_color: str = Field(default="auto", description="'auto' or hex color")


class PatternUpdateRequest(BaseModel):
    """Request to update pattern (e.g., after editing)."""

    grid: Optional[list[list[int]]] = None
    metadata: Optional[PatternMetadataSchema] = None


class ProcessingSettingsSchema(BaseModel):
    """Image processing settings."""

    grid_size: int = 50
    num_colors: int = 8
    dithering: bool = False
    color_space: str = "lab"


class ExportOptionsSchema(BaseModel):
    """Export options."""

    mode: str = Field(default="color", description="'color', 'symbol', or 'sheet'")
    cell_size: int = Field(default=20, ge=10, le=50)
    show_grid: bool = True
    show_legend: bool = True
