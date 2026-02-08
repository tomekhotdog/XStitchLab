"""PDF export functionality for cross-stitch patterns."""

from pathlib import Path
from typing import Optional
import io
from fpdf import FPDF

from ..core.pattern import Pattern
from ..core.thread_calc import ThreadCalculator
from ..core.visualizer import render_color_preview

# ASCII-safe symbols for PDF (Helvetica compatible)
PDF_SYMBOLS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d",
    "e", "f", "g", "h", "i", "j", "k", "l", "m", "n",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
]


def get_pdf_symbol(index: int) -> str:
    """Get an ASCII-safe symbol for PDF export."""
    if index < len(PDF_SYMBOLS):
        return PDF_SYMBOLS[index]
    return str(index)


class PatternPDF(FPDF):
    """Custom PDF class for cross-stitch patterns."""

    def __init__(self, pattern: Pattern):
        super().__init__()
        self.pattern = pattern
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Add header to each page."""
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 10, self.pattern.metadata.title or "Cross-Stitch Pattern", align="L")
        self.ln(5)
        self.set_draw_color(200, 200, 200)
        self.line(10, 15, 200, 15)
        self.ln(10)

    def footer(self):
        """Add footer with page numbers."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class PDFExporter:
    """Export patterns to printable PDF files."""

    def __init__(self, output_dir: Optional[Path | str] = None):
        """Initialize exporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_pattern(
        self,
        pattern: Pattern,
        base_name: str = "pattern",
        include_preview: bool = True,
        include_shopping_list: bool = True,
        fabric_count: int = 14
    ) -> Path:
        """Export pattern to PDF.

        Args:
            pattern: Pattern to export
            base_name: Base filename
            include_preview: Include color preview image
            include_shopping_list: Include thread shopping list
            fabric_count: Fabric count for thread estimation

        Returns:
            Path to exported PDF
        """
        pdf = PatternPDF(pattern)
        pdf.alias_nb_pages()

        # Cover page
        self._add_cover_page(pdf, pattern, include_preview)

        # Color legend page
        self._add_legend_page(pdf, pattern)

        # Symbol grid pages
        self._add_grid_pages(pdf, pattern)

        # Shopping list page
        if include_shopping_list:
            self._add_shopping_list(pdf, pattern, fabric_count)

        # Save PDF
        output_path = self.output_dir / f"{base_name}_pattern.pdf"
        pdf.output(str(output_path))

        return output_path

    def _add_cover_page(
        self,
        pdf: FPDF,
        pattern: Pattern,
        include_preview: bool
    ) -> None:
        """Add cover page with pattern info and preview."""
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 20, pattern.metadata.title or "Cross-Stitch Pattern", align="C")
        pdf.ln(25)

        # Preview image
        if include_preview:
            try:
                preview = render_color_preview(pattern, cell_size=4, show_grid=False)

                # Calculate size to fit on page (max 150mm wide)
                max_width_mm = 150
                aspect = preview.height / preview.width
                img_width = min(max_width_mm, preview.width * 0.3)
                img_height = img_width * aspect

                # Save to bytes
                img_bytes = io.BytesIO()
                preview.save(img_bytes, format="PNG")
                img_bytes.seek(0)

                # Center image
                x = (210 - img_width) / 2  # A4 width is 210mm
                pdf.image(img_bytes, x=x, y=pdf.get_y(), w=img_width, h=img_height)
                pdf.ln(img_height + 10)
            except Exception:
                # Skip preview if it fails
                pass

        # Pattern info
        pdf.set_font("Helvetica", "", 12)
        info_items = [
            f"Dimensions: {pattern.metadata.width} × {pattern.metadata.height} stitches",
            f"Colors: {pattern.metadata.color_count}",
            f"Total Stitches: {pattern.metadata.total_stitches:,}",
            f"Difficulty: {pattern.metadata.difficulty.capitalize()}",
            "",
            "Recommended Fabric Sizes:",
            f"  14-count Aida: {pattern.metadata.fabric_width_inches:.1f}\" × {pattern.metadata.fabric_height_inches:.1f}\"",
        ]

        # Calculate for other fabric counts
        for count in [16, 18]:
            width = pattern.metadata.width / count + 2
            height = pattern.metadata.height / count + 2
            info_items.append(f"  {count}-count Aida: {width:.1f}\" × {height:.1f}\"")

        for item in info_items:
            pdf.cell(0, 8, item, align="C")
            pdf.ln()

    def _add_legend_page(self, pdf: FPDF, pattern: Pattern) -> None:
        """Add color legend page."""
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Color Legend", align="L")
        pdf.ln(15)

        # Table header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)

        col_widths = [15, 20, 50, 25, 40]  # Symbol, Color, DMC Name, Code, Stitches
        headers = ["Sym", "Color", "DMC Name", "Code", "Stitches"]

        for i, (header, width) in enumerate(zip(headers, col_widths)):
            pdf.cell(width, 8, header, border=1, fill=True, align="C")
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 10)

        for i, entry in enumerate(pattern.legend):
            # Symbol (use PDF-safe ASCII symbol)
            pdf.cell(col_widths[0], 8, get_pdf_symbol(i), border=1, align="C")

            # Color swatch
            x, y = pdf.get_x(), pdf.get_y()
            pdf.set_fill_color(*entry.dmc_color.rgb)
            pdf.rect(x + 2, y + 1, col_widths[1] - 4, 6, style="F")
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(col_widths[1], 8, "", border=1)

            # DMC Name
            name = entry.dmc_color.name[:25]  # Truncate long names
            pdf.cell(col_widths[2], 8, name, border=1)

            # DMC Code
            pdf.cell(col_widths[3], 8, entry.dmc_color.code, border=1, align="C")

            # Stitch count
            pdf.cell(col_widths[4], 8, f"{entry.stitch_count:,}", border=1, align="R")

            pdf.ln()

    def _add_grid_pages(self, pdf: FPDF, pattern: Pattern) -> None:
        """Add symbol grid pages."""
        # Calculate grid dimensions for page layout
        # A4 is 210x297mm, with margins ~20mm each side
        usable_width_mm = 170
        usable_height_mm = 240

        # Cell size in mm (aim for readable symbols)
        cell_size_mm = 4

        cells_per_row = int(usable_width_mm / cell_size_mm)
        cells_per_col = int(usable_height_mm / cell_size_mm)

        # Calculate number of pages needed
        pages_x = (pattern.metadata.width + cells_per_row - 1) // cells_per_row
        pages_y = (pattern.metadata.height + cells_per_col - 1) // cells_per_col

        for page_row in range(pages_y):
            for page_col in range(pages_x):
                pdf.add_page()

                # Page title
                pdf.set_font("Helvetica", "B", 10)
                section = f"Section {page_row * pages_x + page_col + 1} of {pages_x * pages_y}"
                pdf.cell(0, 8, section, align="R")
                pdf.ln(5)

                # Calculate grid section
                start_x = page_col * cells_per_row
                start_y = page_row * cells_per_col
                end_x = min(start_x + cells_per_row, pattern.metadata.width)
                end_y = min(start_y + cells_per_col, pattern.metadata.height)

                # Draw grid
                pdf.set_font("Helvetica", "", 7)
                pdf.set_draw_color(200, 200, 200)

                margin_x = 20
                margin_y = pdf.get_y() + 5

                # Draw row numbers
                pdf.set_font("Helvetica", "", 6)
                for row in range(start_y, end_y):
                    if row % 10 == 0:
                        y_pos = margin_y + (row - start_y) * cell_size_mm
                        pdf.set_xy(10, y_pos)
                        pdf.cell(8, cell_size_mm, str(row + 1), align="R")

                # Draw column numbers
                for col in range(start_x, end_x):
                    if col % 10 == 0:
                        x_pos = margin_x + (col - start_x) * cell_size_mm
                        pdf.set_xy(x_pos, margin_y - 4)
                        pdf.cell(cell_size_mm, 4, str(col + 1), align="C")

                # Draw grid cells
                pdf.set_font("Helvetica", "", 6)

                for row in range(start_y, end_y):
                    for col in range(start_x, end_x):
                        x = margin_x + (col - start_x) * cell_size_mm
                        y = margin_y + (row - start_y) * cell_size_mm

                        # Draw cell border
                        if row % 10 == 0 or col % 10 == 0:
                            pdf.set_draw_color(100, 100, 100)
                        else:
                            pdf.set_draw_color(200, 200, 200)

                        pdf.rect(x, y, cell_size_mm, cell_size_mm)

                        # Draw symbol (use PDF-safe ASCII symbol)
                        color_idx = pattern.grid[row][col]
                        if 0 <= color_idx < len(pattern.legend):
                            symbol = get_pdf_symbol(color_idx)
                            pdf.set_xy(x, y)
                            pdf.cell(cell_size_mm, cell_size_mm, symbol, align="C")

    def _add_shopping_list(
        self,
        pdf: FPDF,
        pattern: Pattern,
        fabric_count: int
    ) -> None:
        """Add thread shopping list page."""
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Thread Shopping List", align="L")
        pdf.ln(10)

        # Settings info
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Fabric: {fabric_count}-count Aida")
        pdf.ln()
        pdf.cell(0, 6, "Strands: 2 (standard)")
        pdf.ln()
        pdf.cell(0, 6, "Includes 20% wastage allowance")
        pdf.ln(10)

        # Calculate thread estimates
        calc = ThreadCalculator(fabric_count=fabric_count)
        estimates = calc.estimate_all(pattern)

        # Table
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)

        col_widths = [25, 55, 30, 25, 25]
        headers = ["DMC Code", "Name", "Stitches", "Meters", "Skeins"]

        for header, width in zip(headers, col_widths):
            pdf.cell(width, 8, header, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 10)

        total_skeins = 0
        total_meters = 0.0

        for est in estimates:
            pdf.cell(col_widths[0], 7, est["dmc_code"], border=1, align="C")
            pdf.cell(col_widths[1], 7, est["name"][:28], border=1)
            pdf.cell(col_widths[2], 7, f"{est['stitch_count']:,}", border=1, align="R")
            pdf.cell(col_widths[3], 7, f"{est['meters']:.1f}", border=1, align="R")
            pdf.cell(col_widths[4], 7, str(est["skeins"]), border=1, align="C")
            pdf.ln()

            total_skeins += est["skeins"]
            total_meters += est["meters"]

        # Totals row
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_widths[0] + col_widths[1] + col_widths[2], 8, "TOTAL", border=1, align="R")
        pdf.cell(col_widths[3], 8, f"{total_meters:.1f}m", border=1, align="R")
        pdf.cell(col_widths[4], 8, str(total_skeins), border=1, align="C")


def quick_export_pdf(
    pattern: Pattern,
    output_path: Path | str
) -> Path:
    """Quick export pattern to PDF.

    Args:
        pattern: Pattern to export
        output_path: Full path for output file

    Returns:
        Path to exported file
    """
    output_path = Path(output_path)
    exporter = PDFExporter(output_path.parent)
    return exporter.export_pattern(pattern, output_path.stem)
