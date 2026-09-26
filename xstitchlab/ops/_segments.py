"""Backstitch segment helpers (not an op: skipped by the registry).

Segments use grid-corner coordinates. Every helper normalises direction so that
(x1, y1) <= (x2, y2) lexicographically; `merge_collinear` also sorts its output.
"""

from xstitchlab.core.pattern import Segment
from xstitchlab.ops.base import OpError


def dedupe(segments: list[Segment]) -> list[Segment]:
    """Direction-normalised segments, exact duplicates dropped, first occurrence kept."""
    seen: set[Segment] = set()
    out = []
    for segment in segments:
        n = _normalised(segment)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def split_to_units(segments: list[Segment]) -> list[Segment]:
    """Every segment as its unit steps (axis-aligned or 45-degree only, else OpError)."""
    out = []
    for segment in segments:
        n = _normalised(segment)
        dx, dy = n.x2 - n.x1, n.y2 - n.y1
        length = max(abs(dx), abs(dy))
        if length == 0 or abs(dx) not in (0, length) or abs(dy) not in (0, length):
            raise OpError(f"segment {n} is not axis-aligned or 45-degree")
        sx, sy = dx // length, dy // length
        out.extend(
            Segment(n.x1 + k * sx, n.y1 + k * sy, n.x1 + (k + 1) * sx, n.y1 + (k + 1) * sy)
            for k in range(length)
        )
    return out


def merge_collinear(segments: list[Segment]) -> list[Segment]:
    """Chains of horizontal/vertical unit edges sharing endpoints become one segment each.

    Input may mix unit and longer segments (they are split first); diagonals pass
    through unchanged. Output is de-duplicated and sorted.
    """
    units = dedupe(split_to_units(segments))
    rows: dict[int, list[int]] = {}
    cols: dict[int, list[int]] = {}
    out = []
    for u in units:
        if u.y1 == u.y2:
            rows.setdefault(u.y1, []).append(u.x1)
        elif u.x1 == u.x2:
            cols.setdefault(u.x1, []).append(u.y1)
        else:
            out.append(u)
    for y, xs in rows.items():
        out.extend(Segment(a, y, b, y) for a, b in _runs(xs))
    for x, ys in cols.items():
        out.extend(Segment(x, a, x, b) for a, b in _runs(ys))
    return sorted(out, key=_key)


def _runs(starts: list[int]) -> list[tuple[int, int]]:
    """Maximal [a, b) ranges covered by unit steps starting at each of `starts`."""
    runs = []
    for s in sorted(starts):
        if runs and runs[-1][1] == s:
            runs[-1][1] = s + 1
        else:
            runs.append([s, s + 1])
    return [(a, b) for a, b in runs]


def _normalised(s: Segment) -> Segment:
    return s if (s.x1, s.y1) <= (s.x2, s.y2) else Segment(s.x2, s.y2, s.x1, s.y1)


def _key(s: Segment) -> tuple[int, int, int, int]:
    return (s.x1, s.y1, s.x2, s.y2)
