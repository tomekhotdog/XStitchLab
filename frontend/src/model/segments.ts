/**
 * Backstitch segment helpers, mirroring `xstitchlab/ops/_segments.py`. Segments are grid-corner
 * coordinates; every helper normalises direction so start <= end lexicographically.
 */

import type { Segment } from '@/api/types';

const seg = (x1: number, y1: number, x2: number, y2: number): Segment => ({ start: [x1, y1], end: [x2, y2] });

export function normalise(s: Segment): Segment {
  const [x1, y1] = s.start;
  const [x2, y2] = s.end;
  const ordered = x1 < x2 || (x1 === x2 && y1 <= y2);
  return ordered ? seg(x1, y1, x2, y2) : seg(x2, y2, x1, y1);
}

/** Direction-independent identity of a segment. */
export function segKey(s: Segment): string {
  const n = normalise(s);
  return `${n.start[0]},${n.start[1]}-${n.end[0]},${n.end[1]}`;
}

/** Normalised segments with exact duplicates dropped (first occurrence kept). */
export function dedupe(segments: Segment[]): Segment[] {
  const seen = new Set<string>();
  const out: Segment[] = [];
  for (const s of segments) {
    const n = normalise(s);
    const k = segKey(n);
    if (!seen.has(k)) {
      seen.add(k);
      out.push(n);
    }
  }
  return out;
}

/** Every segment as its unit steps (axis-aligned or 45-degree only, else throws). */
export function splitToUnits(segments: Segment[]): Segment[] {
  const out: Segment[] = [];
  for (const s of segments) {
    const n = normalise(s);
    const dx = n.end[0] - n.start[0];
    const dy = n.end[1] - n.start[1];
    const length = Math.max(Math.abs(dx), Math.abs(dy));
    if (length === 0 || ![0, length].includes(Math.abs(dx)) || ![0, length].includes(Math.abs(dy))) {
      throw new Error(`segment ${segKey(n)} is not axis-aligned or 45-degree`);
    }
    const sx = dx / length;
    const sy = dy / length;
    for (let k = 0; k < length; k++) {
      out.push(seg(n.start[0] + k * sx, n.start[1] + k * sy, n.start[0] + (k + 1) * sx, n.start[1] + (k + 1) * sy));
    }
  }
  return out;
}

const isAxis = (s: Segment) => s.start[0] === s.end[0] || s.start[1] === s.end[1];

const compare = (a: Segment, b: Segment) =>
  a.start[0] - b.start[0] || a.start[1] - b.start[1] || a.end[0] - b.end[0] || a.end[1] - b.end[1];

/** Maximal [a, b) runs covered by unit steps starting at each of `starts`. */
function runs(starts: number[]): [number, number][] {
  const out: [number, number][] = [];
  for (const s of [...starts].sort((a, b) => a - b)) {
    const last = out[out.length - 1];
    if (last && last[1] === s) last[1] = s + 1;
    else out.push([s, s + 1]);
  }
  return out;
}

/**
 * Chains of horizontal/vertical unit edges sharing endpoints become one segment each. Axis-aligned
 * input is split first (so overlaps collapse); anything else is de-duplicated and passed through
 * unchanged. Output is sorted.
 */
export function mergeCollinear(segments: Segment[]): Segment[] {
  const axis = segments.filter(isAxis);
  const other = segments.filter((s) => !isAxis(s));
  const units = dedupe(splitToUnits(axis));
  const rows = new Map<number, number[]>();
  const cols = new Map<number, number[]>();
  for (const u of units) {
    if (u.start[1] === u.end[1]) {
      const y = u.start[1];
      rows.set(y, [...(rows.get(y) ?? []), u.start[0]]);
    } else {
      const x = u.start[0];
      cols.set(x, [...(cols.get(x) ?? []), u.start[1]]);
    }
  }
  const out = dedupe(other);
  for (const [y, xs] of rows) for (const [a, b] of runs(xs)) out.push(seg(a, y, b, y));
  for (const [x, ys] of cols) for (const [a, b] of runs(ys)) out.push(seg(x, a, x, b));
  return out.sort(compare);
}

/** The four unit edges around cell (x, y): top, bottom, left, right. */
export const unitEdgesOfCell = (x: number, y: number): Segment[] => [
  seg(x, y, x + 1, y),
  seg(x, y + 1, x + 1, y + 1),
  seg(x, y, x, y + 1),
  seg(x + 1, y, x + 1, y + 1),
];
