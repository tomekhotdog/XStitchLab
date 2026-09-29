import { beforeEach, describe, expect, it } from 'vitest';
import { useEditorStore } from '@/store/editorStore';
import { at, ctx, grid, loadPattern, makePattern } from '@/test/tools';
import { fill } from './fill';

const store = () => useEditorStore.getState();

beforeEach(() => {
  const p = makePattern(4, 3, 3);
  // a wall of colour 1 down column 2 splits the grid into two regions of colour 0
  p.grid = [
    [0, 0, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 0],
  ];
  loadPattern(p);
});

describe('fill tool', () => {
  it('floods the contiguous region under the pointer with the selected colour and pushes one patch', () => {
    store().setSelectedColour(2);
    fill.onDown(at(0, 0), ctx());
    fill.onUp(at(0, 0), ctx());
    expect(grid()).toEqual([
      [2, 2, 1, 0],
      [2, 2, 1, 0],
      [2, 2, 1, 0],
    ]);
    expect(store().history.undo).toHaveLength(1);
    expect(store().history.undo[0].cells).toHaveLength(6);
    expect(store().history.undo[0].cells).toContainEqual({ x: 1, y: 2, from: 0, to: 2 });
    expect(store().pattern!.legend[2].stitch_count).toBe(6);

    store().undo();
    expect(grid()[0]).toEqual([0, 0, 1, 0]);
  });

  it('is a no-op on a cell that already has the selected colour', () => {
    const before = store().pattern;
    store().setSelectedColour(0);
    fill.onDown(at(1, 1), ctx());
    fill.onUp(at(1, 1), ctx());
    expect(store().pattern).toBe(before);
    expect(store().history.undo).toHaveLength(0);
    expect(store().dirty).toBe(false);
  });

  it('ignores presses off the grid', () => {
    store().setSelectedColour(2);
    fill.onDown(at(9, 9), ctx());
    fill.onUp(at(9, 9), ctx());
    expect(store().history.undo).toHaveLength(0);
  });
});
