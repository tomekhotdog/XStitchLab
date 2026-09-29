import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import * as client from '@/api/client';
import type { Pattern } from '@/api/types';
import { useEditorStore } from './editorStore';
import { useToast } from './toast';

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  return { ...actual, savePattern: vi.fn() };
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

const store = () => useEditorStore.getState();

beforeEach(() => {
  vi.clearAllMocks();
  store().reset();
  useToast.getState().clear();
  useEditorStore.setState({ slug: 'riga' });
  store().setPattern(makePattern());
  const cells = [{ x: 0, y: 0, from: 0, to: 1 }];
  store().setCells(cells);
  store().pushPatch({ cells, backstitchAdd: [], backstitchRemove: [] });
  store().setSelectedColour(1);
  store().setTool('fill');
});

describe('save', () => {
  it('sends the pattern, adopts the canonical result, clears dirty and history, keeps tool state', async () => {
    const edited = store().pattern!;
    const canonical: Pattern = { ...edited, metadata: { ...edited.metadata, total_stitches: 2 } };
    vi.mocked(client.savePattern).mockResolvedValue({ pattern: canonical, version: 'v2' });

    expect(await store().save()).toBe(true);

    expect(client.savePattern).toHaveBeenCalledWith('riga', edited, null);
    expect(store().version).toBe('v2');
    expect(store().pattern).toBe(canonical);
    expect(store().dirty).toBe(false);
    expect(store().history.undo).toHaveLength(0);
    expect(store().saving).toBe(false);
    expect(store().selectedColour).toBe(1);
    expect(store().tool).toBe('fill');
    expect(useToast.getState().message).toBe('Saved');
  });

  it('on error keeps the edited pattern and dirty, and shows a toast', async () => {
    const edited = store().pattern!;
    vi.mocked(client.savePattern).mockRejectedValue(new ApiError(500, 'disk full'));

    expect(await store().save()).toBe(false);

    expect(store().pattern).toBe(edited);
    expect(store().dirty).toBe(true);
    expect(store().history.undo).toHaveLength(1);
    expect(store().saving).toBe(false);
    expect(useToast.getState().message).toBe('disk full');
  });

  it('ignores a second call while one is in flight', async () => {
    let resolve!: (p: { pattern: Pattern; version: string | null }) => void;
    vi.mocked(client.savePattern).mockReturnValue(new Promise((r) => { resolve = r; }));
    const first = store().save();
    expect(store().saving).toBe(true);
    expect(await store().save()).toBe(false);
    resolve({ pattern: store().pattern!, version: 'v2' });
    expect(await first).toBe(true);
    expect(client.savePattern).toHaveBeenCalledTimes(1);
  });

  it('is a no-op without a pattern or slug', async () => {
    store().setPattern(null);
    expect(await store().save()).toBe(false);
    expect(client.savePattern).not.toHaveBeenCalled();
  });
});

describe('save with a version', () => {
  it('sends the loaded version and keeps local edits dirty when the server refuses a stale save', async () => {
    useEditorStore.setState({ version: 'v1' });
    vi.mocked(client.savePattern).mockRejectedValue(
      new ApiError(409, 'design.json changed on disk since you opened it. Reload the design before saving.'),
    );
    const edited = store().pattern!;
    expect(await store().save()).toBe(false);
    expect(client.savePattern).toHaveBeenCalledWith('riga', edited, 'v1');
    expect(store().pattern).toBe(edited);
    expect(store().version).toBe('v1');
    expect(useToast.getState().message).toContain('Reload');
  });
});
