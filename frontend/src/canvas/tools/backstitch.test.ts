import { beforeEach, describe, expect, it } from 'vitest';
import type { Segment } from '@/api/types';
import { useEditorStore } from '@/store/editorStore';
import { ctx, loadPattern, makePattern, onEdge } from '@/test/tools';
import { backstitch } from './backstitch';

const store = () => useEditorStore.getState();
const seg = (x1: number, y1: number, x2: number, y2: number): Segment => ({ start: [x1, y1], end: [x2, y2] });
const segments = () => store().pattern!.backstitch;

beforeEach(() => loadPattern(makePattern(4, 4, 2)));

describe('backstitch tool', () => {
  it('a press adds an absent unit edge and pushes one patch', () => {
    backstitch.onDown(onEdge(seg(1, 1, 2, 1)), ctx());
    backstitch.onUp(onEdge(seg(1, 1, 2, 1)), ctx());
    expect(segments()).toEqual([seg(1, 1, 2, 1)]);
    expect(store().history.undo).toEqual([{ cells: [], backstitchAdd: [seg(1, 1, 2, 1)], backstitchRemove: [] }]);
  });

  it('a press on a present unit edge removes it', () => {
    store().setBackstitch([seg(1, 1, 2, 1)], []);
    backstitch.onDown(onEdge(seg(1, 1, 2, 1)), ctx());
    backstitch.onUp(onEdge(seg(1, 1, 2, 1)), ctx());
    expect(segments()).toEqual([]);
    store().undo();
    expect(segments()).toEqual([seg(1, 1, 2, 1)]);
  });

  it('removing a unit inside a merged segment keeps the rest of it', () => {
    store().setBackstitch([seg(0, 2, 3, 2)], []);
    backstitch.onDown(onEdge(seg(1, 2, 2, 2)), ctx());
    backstitch.onUp(onEdge(seg(1, 2, 2, 2)), ctx());
    expect(segments()).toEqual([seg(0, 2, 1, 2), seg(2, 2, 3, 2)]);
    store().undo();
    expect(segments()).toEqual([seg(0, 2, 3, 2)]);
    store().redo();
    expect(segments()).toEqual([seg(0, 2, 1, 2), seg(2, 2, 3, 2)]);
  });

  it('a drag adds units along the path without removing present ones', () => {
    store().setBackstitch([seg(2, 0, 3, 0)], []);
    backstitch.onDown(onEdge(seg(0, 0, 1, 0)), ctx());
    backstitch.onMove(onEdge(seg(1, 0, 2, 0)), ctx());
    backstitch.onMove(onEdge(seg(2, 0, 3, 0)), ctx());
    backstitch.onMove(onEdge(seg(1, 0, 2, 0)), ctx());
    backstitch.onUp(onEdge(seg(1, 0, 2, 0)), ctx());
    expect(segments()).toEqual([seg(2, 0, 3, 0), seg(0, 0, 1, 0), seg(1, 0, 2, 0)]);
    expect(store().history.undo).toHaveLength(1);
    expect(store().history.undo[0].backstitchAdd).toEqual([seg(0, 0, 1, 0), seg(1, 0, 2, 0)]);
    store().undo();
    expect(segments()).toEqual([seg(2, 0, 3, 0)]);
  });

  it('a press away from any edge does nothing', () => {
    backstitch.onDown({ cell: { x: 1, y: 1 }, edge: null, world: { x: 1.5, y: 1.5 }, native: new MouseEvent('pointerdown') as PointerEvent }, ctx());
    backstitch.onUp({ cell: { x: 1, y: 1 }, edge: null, world: { x: 1.5, y: 1.5 }, native: new MouseEvent('pointerup') as PointerEvent }, ctx());
    expect(store().history.undo).toHaveLength(0);
  });
});
