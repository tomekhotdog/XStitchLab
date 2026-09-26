"""Legend and DMC palette lookups by code (not an op: skipped by the registry)."""

from functools import lru_cache

from xstitchlab.core.pattern import DMCColor, DMCPalette, Pattern, SYMBOLS
from xstitchlab.ops.base import OpError


def index_of_code(pattern: Pattern, code: str) -> int:
    """Legend index of the entry with DMC `code`, else OpError."""
    for i, entry in enumerate(pattern.legend):
        if entry.dmc_color.code == code:
            return i
    raise OpError(f"DMC {code} is not in the legend ({', '.join(e.dmc_color.code for e in pattern.legend)})")


def palette_colour(code: str) -> DMCColor:
    """The DMC palette entry for `code`, else OpError."""
    colour = _palette().get_by_code(code)
    if colour is None:
        raise OpError(f"DMC {code} is not a known DMC colour")
    return colour


def free_symbol(pattern: Pattern) -> str:
    """First standard symbol no legend entry uses (falls back to the entry number)."""
    used = {entry.symbol for entry in pattern.legend}
    return next((s for s in SYMBOLS if s not in used), str(len(pattern.legend)))


@lru_cache(maxsize=1)
def _palette() -> DMCPalette:
    return DMCPalette()
