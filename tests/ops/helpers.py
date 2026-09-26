"""Shared fixtures for op tests."""

from xstitchlab.core.pattern import ColorLegendEntry, DMCColor, Pattern


def small_pattern() -> Pattern:
    """5x5 pattern: white background, black ring, terra cotta centre."""
    symbols = Pattern(grid=[[0]]).SYMBOLS
    colors = [
        DMCColor("3865", "Winter White", (249, 247, 241)),
        DMCColor("310", "Black", (0, 0, 0)),
        DMCColor("3830", "Terra Cotta", (185, 85, 68)),
    ]
    legend = [ColorLegendEntry(c, symbols[i]) for i, c in enumerate(colors)]
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 1, 2, 1, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ]
    return Pattern(grid=grid, legend=legend, background_index=0)


# Distinct DMC colours, one per grid index, for hand-built grids.
_DMC = [
    DMCColor("3865", "Winter White", (249, 247, 241)),
    DMCColor("310", "Black", (0, 0, 0)),
    DMCColor("3830", "Terra Cotta", (185, 85, 68)),
    DMCColor("699", "Green", (5, 101, 23)),
    DMCColor("797", "Royal Blue", (19, 71, 125)),
    DMCColor("444", "Lemon Dark", (255, 214, 0)),
    DMCColor("3799", "Pewter Gray", (66, 66, 66)),
    DMCColor("817", "Coral Red", (187, 5, 31)),
    DMCColor("725", "Topaz", (255, 200, 64)),
    DMCColor("3371", "Black Brown", (30, 17, 8)),
]


def pattern_from_rows(rows: list[str] | str, n_colours: int | None = None, background_index: int | None = 0) -> Pattern:
    """Pattern from rows of digits ("00000/01110/..." or a list of strings), one legend entry per index.

    `n_colours` defaults to the highest digit used + 1; every index gets a distinct DMC code/RGB.
    """
    if isinstance(rows, str):
        rows = rows.split("/")
    grid = [[int(ch) for ch in row] for row in rows]
    if n_colours is None:
        n_colours = max(v for row in grid for v in row) + 1
    symbols = Pattern(grid=[[0]]).SYMBOLS
    legend = [ColorLegendEntry(_DMC[i], symbols[i]) for i in range(n_colours)]
    return Pattern(grid=grid, legend=legend, background_index=background_index)


def rows_of(pattern: Pattern) -> list[str]:
    """Inverse of `pattern_from_rows` for readable assertions."""
    return ["".join(str(v) for v in row) for row in pattern.grid]
