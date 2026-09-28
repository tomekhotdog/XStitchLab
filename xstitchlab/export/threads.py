"""Thread estimates per legend entry, plus the backstitch row: the one source
for design.md, the CLI, the PDF, and the API.

The maths is the kit rule from `designs/_shared/kit-designs.md`: on 14-count
Aida a cross stitch uses ~1.5 cm of 2-strand thread and a backstitch unit edge
~1 cm of 1-strand thread (both with ~20% wastage built in). Kits hold pre-cut
60 cm sections of 6-strand floss, so one section yields 3 x 60 cm of 2-strand
thread (180 cm) or 6 x 60 cm of 1-strand thread (360 cm).
"""

import math

from xstitchlab.core.pattern import Pattern

DMC_SKEIN_LENGTH_METERS = 8.0

CM_PER_STITCH_14CT = 1.5          # 2 strands, wastage included
CM_PER_BACKSTITCH_UNIT_14CT = 1.0  # 1 strand, wastage included
SECTION_CM = 60
FLOSS_STRANDS = 6
CROSS_STRANDS = 2
BACKSTITCH_STRANDS = 1
BACKSTITCH_CODE = "310"
BACKSTITCH_NAME = "Black (Backstitch, 1 strand)"
BACKSTITCH_RGB = (0, 0, 0)


def estimate(pattern: Pattern, *, fabric_count: int | None = None) -> list[dict]:
    """One row per legend entry (legend order), then a backstitch row if any segments.

    Keys: dmc_code, name, rgb, stitch_count, meters, skeins, skeins_decimal,
    sections_60cm, is_background, is_backstitch. The background row keeps its
    cell count but needs no thread; the backstitch row's `stitch_count` is the
    total unit length of the segments.
    """
    pattern.count_stitches()
    count = fabric_count or pattern.metadata.fabric_count or 14
    scale = 14 / count  # thread length scales with cell size
    rows = []
    for idx, entry in enumerate(pattern.legend):
        is_background = idx == pattern.background_index
        cm = 0 if is_background else math.ceil(entry.stitch_count * CM_PER_STITCH_14CT * scale)
        rows.append(_row(
            entry.dmc_color.code, entry.dmc_color.name, tuple(entry.dmc_color.rgb),
            entry.stitch_count, cm, CROSS_STRANDS, is_background=is_background,
        ))
    units = sum(max(abs(s.x2 - s.x1), abs(s.y2 - s.y1)) for s in pattern.backstitch)
    if units:
        cm = math.ceil(units * CM_PER_BACKSTITCH_UNIT_14CT * scale)
        rows.append(_row(
            BACKSTITCH_CODE, BACKSTITCH_NAME, BACKSTITCH_RGB, units, cm, BACKSTITCH_STRANDS,
            is_backstitch=True,
        ))
    return rows


def totals(estimates: list[dict]) -> dict:
    """{stitches (cross stitches only), meters, skeins, sections_60cm} over `estimates`."""
    return {
        "stitches": sum(e["stitch_count"] for e in estimates if not (e["is_background"] or e["is_backstitch"])),
        "meters": round(sum(e["meters"] for e in estimates), 2),
        "skeins": sum(e["skeins"] for e in estimates),
        "sections_60cm": sum(e["sections_60cm"] for e in estimates),
    }


def _row(code, name, rgb, stitch_count, cm, strands, *, is_background=False, is_backstitch=False) -> dict:
    usable_cm_per_section = SECTION_CM * FLOSS_STRANDS // strands
    meters = cm / 100
    skeins_decimal = meters / DMC_SKEIN_LENGTH_METERS
    return {
        "dmc_code": code,
        "name": name,
        "rgb": list(rgb),
        "stitch_count": stitch_count,
        "meters": round(meters, 2),
        "skeins": math.ceil(skeins_decimal),
        "skeins_decimal": round(skeins_decimal, 2),
        "sections_60cm": math.ceil(cm / usable_cm_per_section),
        "is_background": is_background,
        "is_backstitch": is_backstitch,
    }
