import { describe, expect, it } from 'vitest';
import { dedupe, mergeCollinear, normalise, segKey, splitToUnits, unitEdgesOfCell } from './segments';
import type { Segment } from '@/api/types';

const seg = (x1: number, y1: number, x2: number, y2: number): Segment => ({ start: [x1, y1], end: [x2, y2] });

describe('normalise / segKey', () => {
  it('orders endpoints lexicographically', () => {
    expect(normalise(seg(3, 0, 1, 0))).toEqual(seg(1, 0, 3, 0));
    expect(normalise(seg(1, 5, 1, 2))).toEqual(seg(1, 2, 1, 5));
    expect(normalise(seg(0, 0, 1, 1))).toEqual(seg(0, 0, 1, 1));
  });
  it('key is direction-independent', () => {
    expect(segKey(seg(3, 0, 1, 0))).toBe(segKey(seg(1, 0, 3, 0)));
    expect(segKey(seg(1, 0, 3, 0))).not.toBe(segKey(seg(1, 0, 2, 0)));
  });
});

describe('splitToUnits', () => {
  it('splits horizontal, vertical and 45-degree segments', () => {
    expect(splitToUnits([seg(0, 0, 3, 0)])).toEqual([seg(0, 0, 1, 0), seg(1, 0, 2, 0), seg(2, 0, 3, 0)]);
    expect(splitToUnits([seg(2, 4, 2, 2)])).toEqual([seg(2, 2, 2, 3), seg(2, 3, 2, 4)]);
    expect(splitToUnits([seg(0, 2, 2, 0)])).toEqual([seg(0, 2, 1, 1), seg(1, 1, 2, 0)]);
  });
  it('rejects zero-length and off-axis segments', () => {
    expect(() => splitToUnits([seg(1, 1, 1, 1)])).toThrow();
    expect(() => splitToUnits([seg(0, 0, 2, 1)])).toThrow();
  });
});

describe('mergeCollinear', () => {
  it('12 unit edges around a 3x3 block merge to 4 sides', () => {
    const units: Segment[] = [];
    for (let i = 0; i < 3; i++) {
      units.push(seg(i, 0, i + 1, 0), seg(i, 3, i + 1, 3), seg(0, i, 0, i + 1), seg(3, i, 3, i + 1));
    }
    expect(mergeCollinear(units)).toEqual([seg(0, 0, 0, 3), seg(0, 0, 3, 0), seg(0, 3, 3, 3), seg(3, 0, 3, 3)]);
  });

  it('split inverts merge', () => {
    const merged = [seg(0, 0, 3, 0), seg(5, 2, 5, 4)];
    expect(mergeCollinear(splitToUnits(merged))).toEqual(merged);
  });

  it('collapses overlapping runs and gaps stay separate', () => {
    expect(mergeCollinear([seg(0, 0, 2, 0), seg(1, 0, 3, 0), seg(5, 0, 6, 0)])).toEqual([seg(0, 0, 3, 0), seg(5, 0, 6, 0)]);
  });

  it('passes diagonals through, de-duplicated and unsplit', () => {
    const out = mergeCollinear([seg(0, 0, 2, 2), seg(2, 2, 0, 0), seg(0, 0, 1, 0)]);
    expect(out).toEqual([seg(0, 0, 1, 0), seg(0, 0, 2, 2)]);
  });

  it('dedupes reversed duplicates', () => {
    expect(dedupe([seg(1, 0, 0, 0), seg(0, 0, 1, 0)])).toEqual([seg(0, 0, 1, 0)]);
  });
});

describe('unitEdgesOfCell', () => {
  it('returns the four normalised edges', () => {
    expect(unitEdgesOfCell(2, 3)).toEqual([seg(2, 3, 3, 3), seg(2, 4, 3, 4), seg(2, 3, 2, 4), seg(3, 3, 3, 4)]);
  });
});
