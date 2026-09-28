"""`export_design`: write one export of a Design into its folder.

Shared by the CLI (`xstitch export`) and the API (`GET /designs/{slug}/export/{kind}`)
so both produce the same files at the paths `DesignFolder.export_path` names.
"""

from pathlib import Path

from xstitchlab.library.design_folder import DesignFolder

EXPORT_KINDS = ("sheet", "pdf", "png-color", "png-symbol", "png-realistic", "json")
MEDIA_TYPES = {
    "sheet": "text/html",
    "pdf": "application/pdf",
    "png-color": "image/png",
    "png-symbol": "image/png",
    "png-realistic": "image/png",
    "json": "application/json",
}


def export_design(folder: DesignFolder, kind: str, layout: str | None = None) -> Path:
    """Write the export of `kind` for `folder` and return its path.

    `layout` (a4 default, or a5) applies to `sheet` only. `json` rewrites
    design.json in canonical form and regenerates design.md. Raises
    LibraryError for an unknown kind/layout or a folder without a pattern.
    """
    pattern = folder.read_pattern()
    out = folder.export_path(kind, layout)

    if kind == "sheet":
        from xstitchlab.export.pattern_sheet import generate_pattern_sheet
        generate_pattern_sheet(
            pattern, layout=layout or "a4", title=folder.title,
            history=folder.read_history(), output_path=out,
        )
    elif kind == "pdf":
        from xstitchlab.export.pdf_exporter import quick_export_pdf
        quick_export_pdf(pattern, out)
    elif kind == "json":
        folder.write_pattern(pattern)
    else:
        from xstitchlab.core.visualizer import render_color_preview, render_symbol_grid, render_thread_realistic
        render = {
            "png-color": render_color_preview,
            "png-symbol": render_symbol_grid,
            "png-realistic": render_thread_realistic,
        }[kind]
        render(pattern).save(out, "PNG")
    return out
