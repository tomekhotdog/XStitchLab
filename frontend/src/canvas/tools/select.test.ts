import { beforeEach, describe, expect, it } from 'vitest';
import { useEditorStore } from '@/store/editorStore';
import { at, ctx, grid, loadPattern, makePattern } from '@/test/tools';
import { deleteSelection, nudgeSelection, select } from './select';

const store = () => useEditorStore.getState();

/** 4×4 of colour 0 with a 2×2 block of colour 1 at (1,1). */
const block = (background: number | null = null) => {
  const p = makePattern(4, 4, 3, 0, background);
  p.grid = [
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [0, 1, 1, 0],
    [0, 0, 0, 0],
  ];
  return p;
};

const BLOCK = { x: 1, y: 1, w: 2, h: 2 };

beforeEach(() => loadPattern(block()));

describe('marquee', () => {
  it('drag draws a live marquee and commits the normalised rect on up', () => {
    select.onDown(at(2, 2), ctx());
    select.onMove(at(1, 1), ctx());
    expect(store().overlay?.marquee).toEqual(BLOCK);
    expect(store().selection).toBeNull();
    select.onUp(at(1, 1), ctx());
    expect(store().selection).toEqual(BLOCK);
    expect(store().overlay).toBeNull();
    expect(store().dirty).toBe(false);
  });

  it('clamps a drag that leaves the grid to the grid', () => {
    select.onDown(at(2, 2), ctx());
    select.onMove(at(9, 9), ctx());
    select.onUp(at(9, 9), ctx());
    expect(store().selection).toEqual({ x: 2, y: 2, w: 2, h: 2 });
  });

  it('a click without a drag clears the selection', () => {
    store().setSelection(BLOCK);
    select.onDown(at(0, 3), ctx());
    select.onUp(at(0, 3), ctx());
    expect(store().selection).toBeNull();
  });
});

describe('move', () => {
  it('dragging inside the selection previews, then moves the cells by (1,0) and clears the source', () => {
    store().setSelection(BLOCK);
    select.onDown(at(1, 1), ctx());
    select.onMove(at(2, 1), ctx());
    expect(store().overlay?.move).toEqual({ rect: BLOCK, dx: 1, dy: 0 });
    expect(grid()[1]).toEqual([0, 1, 1, 0]); // nothing committed yet
    select.onUp(at(2, 1), ctx());
    expect(grid()).toEqual([
      [0, 0, 0, 0],
      [0, 0, 1, 1],
      [0, 0, 1, 1],
      [0, 0, 0, 0],
    ]);
    expect(store().selection).toEqual({ x: 2, y: 1, w: 2, h: 2 });
    expect(store().overlay).toBeNull();
    expect(store().history.undo).toHaveLength(1);
    store().undo();
    expect(grid()[1]).toEqual([0, 1, 1, 0]);
  });

  it('clears the source to the Background when the pattern has one', () => {
    loadPattern(block(2));
    store().setSelection(BLOCK);
    select.onDown(at(1, 1), ctx());
    select.onMove(at(1, 2), ctx());
    select.onUp(at(1, 2), ctx());
    expect(grid()).toEqual([
      [0, 0, 0, 0],
      [0, 2, 2, 0],
      [0, 1, 1, 0],
      [0, 1, 1, 0],
    ]);
  });

  it('a move past the edge clips the cells and the selection', () => {
    store().setSelection(BLOCK);
    select.onDown(at(2, 2), ctx());
    select.onMove(at(4, 2), ctx()); // off the grid: cell is null, world still tracks
    select.onUp(at(4, 2), ctx());
    expect(grid()).toEqual([
      [0, 0, 0, 0],
      [0, 0, 0, 1],
      [0, 0, 0, 1],
      [0, 0, 0, 0],
    ]);
    expect(store().selection).toEqual({ x: 3, y: 1, w: 1, h: 2 });
  });

  it('a move entirely off the grid clears the cells and the selection', () => {
    store().setSelection(BLOCK);
    select.onDown(at(1, 1), ctx());
    select.onMove(at(1, 5), ctx());
    select.onUp(at(1, 5), ctx());
    expect(grid().flat().every((v) => v === 0)).toBe(true);
    expect(store().selection).toBeNull();
  });

  it('a drag inside the selection that ends where it started changes nothing', () => {
    store().setSelection(BLOCK);
    const before = store().pattern;
    select.onDown(at(1, 1), ctx());
    select.onMove(at(2, 1), ctx());
    select.onMove(at(1, 1), ctx());
    select.onUp(at(1, 1), ctx());
    expect(store().pattern).toBe(before);
    expect(store().selection).toEqual(BLOCK);
    expect(store().history.undo).toHaveLength(0);
  });
});

describe('deleteSelection', () => {
  it('sets the selection to the Background (0 without one) and pushes a patch', () => {
    store().setSelection(BLOCK);
    deleteSelection(ctx());
    expect(grid().flat().every((v) => v === 0)).toBe(true);
    expect(store().history.undo).toHaveLength(1);
    expect(store().selection).toEqual(BLOCK);
  });

  it('uses the Background index when set', () => {
    loadPattern(block(2));
    store().setSelection({ x: 1, y: 1, w: 1, h: 1 });
    deleteSelection(ctx());
    expect(grid()[1]).toEqual([0, 2, 1, 0]);
  });

  it('does nothing without a selection', () => {
    deleteSelection(ctx());
    expect(store().history.undo).toHaveLength(0);
  });
});

describe('nudgeSelection', () => {
  it('moves the cells and the selection by one cell', () => {
    store().setSelection(BLOCK);
    nudgeSelection(ctx(), 0, -1);
    expect(grid()).toEqual([
      [0, 1, 1, 0],
      [0, 1, 1, 0],
      [0, 0, 0, 0],
      [0, 0, 0, 0],
    ]);
    expect(store().selection).toEqual({ x: 1, y: 0, w: 2, h: 2 });
    expect(store().history.undo).toHaveLength(1);
  });
});
