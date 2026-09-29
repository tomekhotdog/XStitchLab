import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import * as client from '@/api/client';
import type { Pattern } from '@/api/types';
import { useEditorStore } from './editorStore';
import { useToast } from './toast';

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  return { ...actual, applyOp: vi.fn() };
});

const makePattern = (): Pattern => ({
  metadata: {
    title: 't', width: 2, height: 1, color_count: 2, total_stitches: 2, difficulty: 'easy',
    fabric_count: 14, fabric_width_inches: 1, fabric_height_inches: 1, source_image: null,
  },
  legend: [
    { symbol: '·', dmc_code: 'B5200', dmc_name: 'Snow White', rgb: [255, 255, 255], stitch_count: 1 },
    { symbol: '■', dmc_code: '938', dmc_name: 'Coffee', rgb: [54, 31, 14], stitch_count: 1 },
  ],
  grid: [[0, 1]],
  backstitch: [],
  background_index: null,
  recipe: [],
});

/** What `merge_colours 938 -> B5200` would return: one legend entry, every cell 0. */
const merged = (): Pattern => ({
  ...makePattern(),
  legend: [{ symbol: '·', dmc_code: 'B5200', dmc_name: 'Snow White', rgb: [255, 255, 255], stitch_count: 2 }],
  grid: [[0, 0]],
});

const store = () => useEditorStore.getState();

beforeEach(() => {
  vi.clearAllMocks();
  store().reset();
  useToast.getState().clear();
  useEditorStore.setState({ slug: 'riga' });
  store().setPattern(makePattern());
});

describe('applyOp', () => {
  it('replaces the pattern, pushes a replace patch, marks dirty', async () => {
    const before = store().pattern!;
    const after = merged();
    vi.mocked(client.applyOp).mockResolvedValue(after);
    store().setSelectedColour(1);

    expect(await store().applyOp('merge_colours', { from_dmc: '938', to_dmc: 'B5200' })).toBe(true);

    expect(client.applyOp).toHaveBeenCalledWith(before, 'merge_colours', { from_dmc: '938', to_dmc: 'B5200' });
    expect(store().pattern).toBe(after);
    expect(store().dirty).toBe(true);
    expect(store().history.undo).toHaveLength(1);
    expect(store().history.undo[0].replace).toEqual({ before, after });
    expect(store().selectedColour).toBe(0); // clamped to the shorter legend
  });

  it('undo restores the previous pattern and redo reapplies', async () => {
    const before = store().pattern!;
    const after = merged();
    vi.mocked(client.applyOp).mockResolvedValue(after);
    await store().applyOp('merge_colours', { from_dmc: '938', to_dmc: 'B5200' });

    store().undo();
    expect(store().pattern).toBe(before);
    expect(store().canRedo()).toBe(true);

    store().redo();
    expect(store().pattern).toBe(after);
    expect(store().canUndo()).toBe(true);
  });

  it('cell patches before and after a replace still undo in order', async () => {
    const cells = [{ x: 0, y: 0, from: 0, to: 1 }];
    store().setCells(cells);
    store().pushPatch({ cells, backstitchAdd: [], backstitchRemove: [] });
    vi.mocked(client.applyOp).mockResolvedValue(merged());
    await store().applyOp('merge_colours', { from_dmc: '938', to_dmc: 'B5200' });

    store().undo();
    expect(store().pattern!.grid).toEqual([[1, 1]]);
    store().undo();
    expect(store().pattern!.grid).toEqual([[0, 1]]);
    expect(store().canUndo()).toBe(false);
  });

  it('on error leaves the pattern and history alone and shows a toast', async () => {
    const before = store().pattern!;
    vi.mocked(client.applyOp).mockRejectedValue(new ApiError(400, 'unknown DMC code 9999'));

    expect(await store().applyOp('substitute_colour', { from_dmc: '938', to_dmc: '9999' })).toBe(false);

    expect(store().pattern).toBe(before);
    expect(store().dirty).toBe(false);
    expect(store().history.undo).toHaveLength(0);
    expect(useToast.getState().message).toBe('unknown DMC code 9999');
  });

  it('is a no-op without a pattern', async () => {
    store().setPattern(null);
    expect(await store().applyOp('background_to_fabric', {})).toBe(false);
    expect(client.applyOp).not.toHaveBeenCalled();
  });
});
