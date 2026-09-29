import { describe, expect, it } from 'vitest';
import { applyChanges, cloneGrid, floodFill, invertChanges, moveRect, rectCells } from './grid';

const G = () => [
  [0, 0, 1, 1],
  [0, 0, 1, 2],
  [3, 3, 3, 3],
];

describe('cloneGrid', () => {
  it('is a deep copy', () => {
    const g = G();
    const c = cloneGrid(g);
    c[0][0] = 9;
    expect(g[0][0]).toBe(0);
    expect(c).not.toBe(g);
    expect(c[1]).not.toBe(g[1]);
  });
});

describe('floodFill', () => {
  it('fills a 4-connected region only', () => {
    const changes = floodFill(G(), 0, 0, 7);
    const cells = changes.map((c) => `${c.x},${c.y}`).sort();
    expect(cells).toEqual(['0,0', '0,1', '1,0', '1,1']);
    expect(changes.every((c) => c.from === 0 && c.to === 7)).toBe(true);
  });

  it('does not leak diagonally', () => {
    const g = [
      [1, 0],
      [0, 1],
    ];
    const changes = floodFill(g, 0, 0, 5);
    expect(changes).toEqual([{ x: 0, y: 0, from: 1, to: 5 }]);
  });

  it('is a no-op when the value is unchanged', () => {
    expect(floodFill(G(), 0, 0, 0)).toEqual([]);
  });

  it('is empty outside the grid', () => {
    expect(floodFill(G(), 4, 0, 1)).toEqual([]);
    expect(floodFill(G(), -1, 0, 1)).toEqual([]);
    expect(floodFill(G(), 0, 3, 1)).toEqual([]);
  });

  it('does not mutate the grid', () => {
    const g = G();
    floodFill(g, 2, 0, 9);
    expect(g).toEqual(G());
  });
});

describe('rectCells', () => {
  it('lists cells row-major', () => {
    expect(rectCells({ x: 1, y: 0, w: 2, h: 2 })).toEqual([
      { x: 1, y: 0 }, { x: 2, y: 0 }, { x: 1, y: 1 }, { x: 2, y: 1 },
    ]);
  });
  it('is empty for a degenerate rect', () => {
    expect(rectCells({ x: 1, y: 1, w: 0, h: 3 })).toEqual([]);
  });
});

describe('moveRect', () => {
  it('moving a 2x2 block right by 1 is overlap-safe', () => {
    const g = [
      [1, 2, 0],
      [3, 4, 0],
    ];
    const changes = moveRect(g, { x: 0, y: 0, w: 2, h: 2 }, 1, 0, 0);
    expect(applyChanges(g, changes)).toEqual([
      [0, 1, 2],
      [0, 3, 4],
    ]);
  });

  it('moving left by 1 is also overlap-safe', () => {
    const g = [
      [0, 1, 2],
      [0, 3, 4],
    ];
    const changes = moveRect(g, { x: 1, y: 0, w: 2, h: 2 }, -1, 0, 0);
    expect(applyChanges(g, changes)).toEqual([
      [1, 2, 0],
      [3, 4, 0],
    ]);
  });

  it('clears the source with `fill` and clips at the bounds', () => {
    const g = [
      [1, 2],
      [3, 4],
    ];
    const changes = moveRect(g, { x: 0, y: 0, w: 2, h: 2 }, 1, 1, 9);
    expect(applyChanges(g, changes)).toEqual([
      [9, 9],
      [9, 1],
    ]);
  });

  it('with dx=dy=0 yields no changes', () => {
    expect(moveRect(G(), { x: 0, y: 0, w: 2, h: 2 }, 0, 0, 0)).toEqual([]);
  });

  it('every change records the value present when it is applied (invertible)', () => {
    const g = [
      [1, 2, 0],
      [3, 4, 0],
    ];
    const changes = moveRect(g, { x: 0, y: 0, w: 2, h: 2 }, 1, 0, 0);
    const moved = applyChanges(g, changes);
    expect(applyChanges(moved, invertChanges(changes))).toEqual(g);
  });
});

describe('applyChanges / invertChanges', () => {
  it('round-trips and leaves the input untouched (copy-on-write rows)', () => {
    const g = G();
    const changes = [
      { x: 0, y: 0, from: 0, to: 5 },
      { x: 3, y: 2, from: 3, to: 6 },
    ];
    const next = applyChanges(g, changes);
    expect(next[0][0]).toBe(5);
    expect(next[2][3]).toBe(6);
    expect(g).toEqual(G());
    expect(next[1]).toBe(g[1]); // untouched row shares its reference
    expect(next[0]).not.toBe(g[0]);
    expect(applyChanges(next, invertChanges(changes))).toEqual(G());
  });

  it('invertChanges reverses order and swaps from/to', () => {
    expect(invertChanges([
      { x: 0, y: 0, from: 1, to: 2 },
      { x: 0, y: 0, from: 2, to: 3 },
    ])).toEqual([
      { x: 0, y: 0, from: 3, to: 2 },
      { x: 0, y: 0, from: 2, to: 1 },
    ]);
  });
});
