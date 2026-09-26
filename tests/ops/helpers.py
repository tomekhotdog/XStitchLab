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
