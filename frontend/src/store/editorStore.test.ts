import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HISTORY_CAP, useEditorStore } from './editorStore';
import type { Pattern } from '@/api/types';

const makePattern = (): Pattern => ({
  metadata: {
    title: 't', width: 3, height: 2, color_count: 2, total_stitches: 6, difficulty: 'easy',
    fabric_count: 14, fabric_width_inches: 1, fabric_height_inches: 1, source_image: null,
  },
  legend: [
    { symbol: '·', dmc_code: 'B5200', dmc_name: 'Snow White', rgb: [255, 255, 255], stitch_count: 4 },
    { symbol: '■', dmc_code: '938', dmc_name: 'Coffee', rgb: [54, 31, 14], stitch_count: 2 },
  ],
  grid: [
    [0, 0, 1],
    [0, 0, 1],
  ],
  backstitch: [{ start: [0, 0], end: [3, 0] }],
  background_index: null,
  recipe: [],
});

const store = () => useEditorStore.getState();

beforeEach(() => {
  useEditorStore.getState().reset();
  useEditorStore.getState().setPattern(makePattern());
});

describe('setCells', () => {
  it('applies changes immutably, keeps legend counts in sync and marks dirty', () => {
    const before = store().pattern!;
    store().setCells([{ x: 0, y: 0, from: 0, to: 1 }]);
    const after = store().pattern!;
    expect(after.grid[0][0]).toBe(1);
    expect(after).not.toBe(before);
    expect(before.grid[0][0]).toBe(0);
    expect(after.legend[0].stitch_count).toBe(3);
    expect(after.legend[1].stitch_count).toBe(3);
    expect(store().dirty).toBe(true);
  });

  it('ignores an empty change list', () => {
    const before = store().pattern;
    store().setCells([]);
    expect(store().pattern).toBe(before);
    expect(store().dirty).toBe(false);
  });
});

describe('setBackstitch', () => {
  it('removes then adds, de-duplicated by key regardless of direction', () => {
    store().setBackstitch([{ start: [1, 1], end: [0, 1] }, { start: [0, 1], end: [1, 1] }], [{ start: [3, 0], end: [0, 0] }]);
    expect(store().pattern!.backstitch).toEqual([{ start: [0, 1], end: [1, 1] }]);
    expect(store().dirty).toBe(true);
  });
});

describe('setBackground', () => {
  it('sets and clears the background index', () => {
    store().setBackground(1);
    expect(store().pattern!.background_index).toBe(1);
    store().setBackground(null);
    expect(store().pattern!.background_index).toBeNull();
  });
});

describe('undo / redo', () => {
  it('undo restores cells and backstitch; redo reapplies', () => {
    const cells = [{ x: 0, y: 0, from: 0, to: 1 }, { x: 1, y: 0, from: 0, to: 1 }];
    const add = [{ start: [0, 1], end: [1, 1] }] as Pattern['backstitch'];
    const remove = [{ start: [0, 0], end: [3, 0] }] as Pattern['backstitch'];
    store().setCells(cells);
    store().setBackstitch(add, remove);
    store().pushPatch({ cells, backstitchAdd: add, backstitchRemove: remove });
    expect(store().pattern!.grid[0]).toEqual([1, 1, 1]);
    expect(store().canUndo()).toBe(true);
    expect(store().canRedo()).toBe(false);

    store().undo();
    expect(store().pattern!.grid[0]).toEqual([0, 0, 1]);
    expect(store().pattern!.backstitch).toEqual(remove);
    expect(store().pattern!.legend[0].stitch_count).toBe(4);
    expect(store().canRedo()).toBe(true);

    store().redo();
    expect(store().pattern!.grid[0]).toEqual([1, 1, 1]);
    expect(store().pattern!.backstitch).toEqual(add);
    expect(store().canRedo()).toBe(false);
  });

  it('undo goes through the setters so subscribers see it', () => {
    const seen = vi.fn();
    const unsub = useEditorStore.subscribe((s, prev) => {
      if (s.pattern !== prev.pattern) seen(s.pattern!.grid[0][0]);
    });
    const cells = [{ x: 0, y: 0, from: 0, to: 1 }];
    store().setCells(cells);
    store().pushPatch({ cells, backstitchAdd: [], backstitchRemove: [] });
    store().undo();
    unsub();
    expect(seen.mock.calls.map((c) => c[0])).toEqual([1, 0]);
  });

  it('a new patch clears the redo stack', () => {
    const p = (to: number) => ({ cells: [{ x: 0, y: 0, from: 0, to }], backstitchAdd: [], backstitchRemove: [] });
    store().pushPatch(p(1));
    store().undo();
    expect(store().canRedo()).toBe(true);
    store().pushPatch(p(2));
    expect(store().canRedo()).toBe(false);
  });

  it('undo/redo with empty stacks are no-ops', () => {
    const before = store().pattern;
    store().undo();
    store().redo();
    expect(store().pattern).toBe(before);
  });

  it(`history is capped at ${HISTORY_CAP} entries, dropping the oldest`, () => {
    for (let i = 0; i < HISTORY_CAP + 5; i++) {
      store().pushPatch({ cells: [{ x: 0, y: 0, from: i, to: i + 1 }], backstitchAdd: [], backstitchRemove: [] });
    }
    expect(store().history.undo).toHaveLength(HISTORY_CAP);
    expect(store().history.undo[0].cells[0].from).toBe(5);
  });
});

describe('setPattern', () => {
  it('replaces the pattern, clears history and dirty', () => {
    store().pushPatch({ cells: [{ x: 0, y: 0, from: 0, to: 1 }], backstitchAdd: [], backstitchRemove: [] });
    expect(store().dirty).toBe(true);
    store().setPattern(makePattern());
    expect(store().dirty).toBe(false);
    expect(store().history.undo).toHaveLength(0);
    expect(store().history.redo).toHaveLength(0);
  });
});

describe('selection state', () => {
  it('tool, colour and selection setters', () => {
    store().setTool('fill');
    store().setSelectedColour(1);
    store().setSelection({ x: 0, y: 0, w: 2, h: 1 });
    expect(store().tool).toBe('fill');
    expect(store().selectedColour).toBe(1);
    expect(store().selection).toEqual({ x: 0, y: 0, w: 2, h: 1 });
  });
});

describe('load', () => {
  it('fetches the design and adopts its pattern and recipe', async () => {
    const pattern = { ...makePattern(), recipe: [{ op: 'pixelate', params: { width: 3 } }] };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      slug: 's', title: 'T', prompt: '', has_input: true, pattern, history: '',
    }), { status: 200 })));
    await store().load('s');
    vi.unstubAllGlobals();
    expect(store().slug).toBe('s');
    expect(store().design?.title).toBe('T');
    expect(store().pattern?.recipe).toEqual(pattern.recipe);
    expect(store().recipe).toEqual(pattern.recipe);
    expect(store().status.kind).toBe('idle');
  });

  it('reports an error status when the design is missing', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'nope' }), { status: 404 })));
    await store().load('missing');
    vi.unstubAllGlobals();
    expect(store().status).toEqual({ kind: 'error', message: 'nope' });
    expect(store().pattern).toBeNull();
  });
});
