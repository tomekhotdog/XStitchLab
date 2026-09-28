"""Render `design.md` (the per-design kit notes) from a Pattern.

Layout, matching the committed files: the `# ` heading, an optional
`**Description:**` line, a stats table, the thread table with 60 cm sections
per kit, a background note, then everything the designer wrote by hand
(`## Label Text`, `## Design Files`, ...) carried over verbatim. Heading and
description are kept from the existing file when there is one, since they
carry the kit number and the label copy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xstitchlab.core.pattern import Pattern
from xstitchlab.export import threads

if TYPE_CHECKING:
    from xstitchlab.library.design_folder import DesignFolder

THREAD_TABLE_HEADING = "## Thread Table"
THREAD_TABLE_HEADER = (
    "| Colour | DMC | Stitches | Thread needed | 60cm sections per kit |\n"
    "|--------|-----|----------|---------------|----------------------|"
)
DESCRIPTION_PREFIX = "**Description:**"


def render(pattern: Pattern, folder: "DesignFolder") -> str:
    existing = folder.design_md_path.read_text() if folder.design_md_path.is_file() else ""
    heading, description, tail = split_existing(existing)
    heading = heading or f"# {pattern.metadata.title or folder.slug}"

    rows = threads.estimate(pattern)
    total = threads.totals(rows)
    lines = [heading, ""]
    if description:
        lines += [description, ""]
    lines += [
        "| | |",
        "|---|---|",
        f"| **Stitches** | {total['stitches']:,} |",
        f"| **Difficulty** | {pattern.metadata.difficulty.capitalize()} |",
        f"| **Colours** | {len(pattern.legend)} |",
        f"| **Total thread** | {total['meters']:.1f}m |",
        "",
        THREAD_TABLE_HEADING,
        "",
        THREAD_TABLE_HEADER,
    ]
    for row in rows:
        if row["is_background"]:
            continue
        cm = round(row["meters"] * 100)
        if row["is_backstitch"]:
            stitches, thread = f"{row['stitch_count']} segs", f"{cm}cm (1-strand)"
        else:
            stitches, thread = str(row["stitch_count"]), f"{cm}cm (2-strand)"
        lines.append(f"| {row['name']} | {row['dmc_code']} | {stitches} | {thread} | {row['sections_60cm']} |")
    lines.append(f"| | | | **Total sections per kit** | **{total['sections_60cm']}** |")

    background = pattern.background_index
    if background is not None and 0 <= background < len(pattern.legend):
        colour = pattern.legend[background].dmc_color
        label = colour.name if colour.code == colour.name else f"DMC {colour.code} ({colour.name})"
        lines += ["", f"*Note: {label} is the background colour and is not stitched.*"]
    if tail:
        lines += ["", tail]
    return "\n".join(lines).rstrip("\n") + "\n"


def split_existing(markdown: str) -> tuple[str, str, str]:
    """(heading line, description line, hand-written tail) found in an existing design.md.

    The tail starts at the first `## ` heading other than the thread table and
    runs to the end of the file; each part is "" when absent.
    """
    lines = markdown.splitlines()
    heading = next((l for l in lines if l.startswith("# ")), "")
    description = next((l for l in lines if l.startswith(DESCRIPTION_PREFIX)), "")
    tail = ""
    for i, line in enumerate(lines):
        if line.startswith("## ") and line.strip() != THREAD_TABLE_HEADING:
            tail = "\n".join(lines[i:]).rstrip("\n")
            break
    return heading, description, tail
