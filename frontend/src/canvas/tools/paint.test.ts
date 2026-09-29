import { beforeEach, describe, expect, it } from 'vitest';
import { useEditorStore } from '@/store/editorStore';
import { at, ctx, grid, loadPattern, makePattern } from '@/test/tools';
import { lineCells, paint } from './paint';

const store = () => useEditorStore.getState();

beforeEach(() => {
  loadPattern(makePattern(5, 5, 2));
  store().setSelectedColour(1);
});

describe('lineCells', () => {
  it('walks from a (exclusive) to b (inclusive) without gaps', () => {
    expect(lineCells({ x: 0, y: 0 }, { x: 3, y: 1 })).toEqual([{ x: 1, y: 0 }, { x: 2, y: 1 }, { x: 3, y: 1 }]);
    expect(lineCells({ x: 2, y: 2 }, { x: 2, y: 2 })).toEqual([]);
    expect(lineCells({ x: 4, y: 4 }, { x: 4, y: 2 })).toEqual([{ x: 4, y: 3 }, { x: 4, y: 2 }]);
  });
});

describe('paint tool', () => {
  it('a press paints one cell and a stroke is one patch', () => {
    paint.onDown(at(1, 1), ctx());
    paint.onUp(at(1, 1), ctx());
    expect(grid()[1][1]).toBe(1);
    expect(store().history.undo).toHaveLength(1);
    expect(store().history.undo[0].cells).toEqual([{ x: 1, y: 1, from: 0, to: 1 }]);
  });

  it('a fast drag leaves no holes and records each cell once', () => {
    paint.onDown(at(0, 0), ctx());
    paint.onMove(at(4, 4), ctx());
    paint.onMove(at(4, 4), ctx());
    paint.onUp(at(4, 4), ctx());
    expect([0, 1, 2, 3, 4].map((i) => grid()[i][i])).toEqual([1, 1, 1, 1, 1]);
    expect(store().history.undo).toHaveLength(1);
    expect(store().history.undo[0].cells).toHaveLength(5);
    store().undo();
    expect(grid().flat().every((v) => v === 0)).toBe(true);
  });

  it('painting the selected colour over itself is a no-op', () => {
    store().setSelectedColour(0);
    paint.onDown(at(2, 2), ctx());
    paint.onUp(at(2, 2), ctx());
    expect(store().history.undo).toHaveLength(0);
    expect(store().dirty).toBe(false);
  });

  it('leaving the grid mid-stroke breaks the line rather than bridging across', () => {
    paint.onDown(at(0, 0), ctx());
    paint.onMove(at(9, 9), ctx());
    paint.onMove(at(4, 0), ctx());
    paint.onUp(at(4, 0), ctx());
    expect(grid()[0]).toEqual([1, 0, 0, 0, 1]);
  });
});
