import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import * as client from '@/api/client';
import type { OpCall, OpSchema, Pattern, Step } from '@/api/types';
import { useEditorStore } from './editorStore';

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  return { ...actual, runRecipe: vi.fn(), listOps: vi.fn(), defaultRecipes: vi.fn() };
});

const schema = (name: string, kind: OpSchema['kind'], properties: Record<string, unknown>): OpSchema => ({
  name, kind, group: 'g', title: name, description: '', schema: { type: 'object', properties },
});

const SCHEMAS: OpSchema[] = [
  schema('quantize_image', 'image', {
    method: { type: 'string', enum: ['kmeans', 'median_cut'], default: 'kmeans' },
    n_colors: { type: 'integer', minimum: 2, maximum: 64, default: 8 },
    dither: { type: 'boolean', default: false },
  }),
  schema('pixelate', 'pixelate', {
    width: { type: 'integer', minimum: 4, maximum: 400, default: 50 },
    height: { anyOf: [{ type: 'integer' }, { type: 'null' }], default: null },
    sample: { type: 'string', enum: ['majority', 'nearest'], default: 'majority' },
  }),
  schema('remove_isolated', 'pattern', {}),
  schema('generate_backstitch', 'pattern', { min_contrast: { type: 'integer', default: 50 } }),
];

const DEFAULTS: Record<string, OpCall[]> = {
  predesigned: [
    { op: 'quantize_image', params: { method: 'kmeans', n_colors: 8 } },
    { op: 'pixelate', params: { width: 50 } },
  ],
  photo: [{ op: 'pixelate', params: { width: 50, sample: 'nearest' } }],
};

const makePattern = (recipe: OpCall[] = []): Pattern => ({
  metadata: {
    title: 't', width: 2, height: 1, color_count: 1, total_stitches: 2, difficulty: 'easy',
    fabric_count: 14, fabric_width_inches: 1, fabric_height_inches: 1, source_image: null,
  },
  legend: [{ symbol: '·', dmc_code: 'B5200', dmc_name: 'Snow White', rgb: [255, 255, 255], stitch_count: 2 }],
  grid: [[0, 0]],
  backstitch: [],
  background_index: null,
  recipe,
});

const store = () => useEditorStore.getState();

beforeEach(() => {
  vi.clearAllMocks();
  store().reset();
  useEditorStore.setState({ slug: 'riga', opSchemas: SCHEMAS, defaults: DEFAULTS });
});

describe('loadOps', () => {
  it('fetches schemas and defaults once', async () => {
    useEditorStore.setState({ opSchemas: [], defaults: {} });
    vi.mocked(client.listOps).mockResolvedValue(SCHEMAS);
    vi.mocked(client.defaultRecipes).mockResolvedValue(DEFAULTS);
    await store().loadOps();
    await store().loadOps();
    expect(client.listOps).toHaveBeenCalledTimes(1);
    expect(store().opSchemas).toEqual(SCHEMAS);
    expect(store().defaults).toEqual(DEFAULTS);
  });
});

describe('addOp', () => {
  it('appends with the schema defaults, omitting null defaults', () => {
    expect(store().addOp('quantize_image')).toBe(true);
    expect(store().addOp('pixelate')).toBe(true);
    expect(store().recipe).toEqual([
      { op: 'quantize_image', params: { method: 'kmeans', n_colors: 8, dither: false } },
      { op: 'pixelate', params: { width: 50, sample: 'majority' } },
    ]);
  });

  it('places a pattern op after the pixelate when the chosen index would precede it', () => {
    store().setRecipe([{ op: 'quantize_image', params: {} }, { op: 'pixelate', params: {} }]);
    expect(store().addOp('remove_isolated', 0)).toBe(true);
    expect(store().recipe.map((c) => c.op)).toEqual(['quantize_image', 'pixelate', 'remove_isolated']);
  });

  it('inserts a pattern op at a valid chosen index', () => {
    store().setRecipe([{ op: 'pixelate', params: {} }, { op: 'generate_backstitch', params: {} }]);
    store().addOp('remove_isolated', 1);
    expect(store().recipe.map((c) => c.op)).toEqual(['pixelate', 'remove_isolated', 'generate_backstitch']);
  });

  it('keeps an image op before the pixelate', () => {
    store().setRecipe([{ op: 'pixelate', params: {} }, { op: 'remove_isolated', params: {} }]);
    store().addOp('quantize_image');
    expect(store().recipe.map((c) => c.op)).toEqual(['quantize_image', 'pixelate', 'remove_isolated']);
  });

  it('refuses a second pixelate', () => {
    store().setRecipe([{ op: 'pixelate', params: {} }]);
    expect(store().addOp('pixelate')).toBe(false);
    expect(store().recipe).toHaveLength(1);
  });

  it('refuses an unknown op', () => {
    expect(store().addOp('nope')).toBe(false);
  });
});

describe('recipe edits are immutable', () => {
  const base: OpCall[] = [
    { op: 'quantize_image', params: { n_colors: 8 } },
    { op: 'pixelate', params: { width: 50 } },
    { op: 'remove_isolated', params: {} },
  ];

  it('removeOp', () => {
    store().setRecipe(base);
    const before = store().recipe;
    store().removeOp(2);
    expect(store().recipe.map((c) => c.op)).toEqual(['quantize_image', 'pixelate']);
    expect(before).toHaveLength(3);
  });

  it('moveOp', () => {
    store().setRecipe(base);
    const before = store().recipe;
    store().moveOp(2, 1);
    expect(store().recipe.map((c) => c.op)).toEqual(['quantize_image', 'remove_isolated', 'pixelate']);
    expect(before.map((c) => c.op)).toEqual(['quantize_image', 'pixelate', 'remove_isolated']);
    store().moveOp(0, 5); // out of range: no-op
    expect(store().recipe.map((c) => c.op)).toEqual(['quantize_image', 'remove_isolated', 'pixelate']);
  });

  it('setParam replaces the call and params objects; null removes the key', () => {
    store().setRecipe(base);
    const before = store().recipe;
    store().setParam(0, 'n_colors', 12);
    const after = store().recipe;
    expect(after[0].params).toEqual({ n_colors: 12 });
    expect(before[0].params).toEqual({ n_colors: 8 });
    expect(after[0]).not.toBe(before[0]);
    expect(after[1]).toBe(before[1]);
    store().setParam(0, 'n_colors', null);
    expect(store().recipe[0].params).toEqual({});
  });
});

describe('loadDefault', () => {
  it('deep-copies so recipe edits never touch the defaults', () => {
    store().loadDefault('predesigned');
    store().setParam(0, 'n_colors', 3);
    store().recipe[1].params.width = 999; // even a direct mutation
    expect(store().defaults.predesigned[0].params.n_colors).toBe(8);
    expect(store().defaults.predesigned[1].params.width).toBe(50);
  });

  it('ignores an unknown default', () => {
    store().setRecipe([{ op: 'pixelate', params: {} }]);
    store().loadDefault('nope');
    expect(store().recipe).toHaveLength(1);
  });
});

describe('runRecipe', () => {
  const recipe: OpCall[] = [{ op: 'pixelate', params: { width: 2 } }];
  const steps: Step[] = [{ name: 'pixelate', params: { width: 2 }, kind: 'pixelate', preview_png: 'AAAA', stats: { width: 2, height: 1 } }];

  it('replaces pattern and steps, adopts the returned recipe, clears history and dirty', async () => {
    store().setPattern(makePattern());
    store().pushPatch({ cells: [{ x: 0, y: 0, from: 0, to: 0 }], backstitchAdd: [], backstitchRemove: [] });
    store().setPreviewStep(0);
    store().setRecipe(recipe);
    const returned = makePattern(recipe);
    vi.mocked(client.runRecipe).mockResolvedValue({ pattern: returned, steps });

    const p = store().runRecipe();
    expect(store().running).toBe(true);
    await p;

    expect(client.runRecipe).toHaveBeenCalledWith('riga', recipe);
    expect(store().running).toBe(false);
    expect(store().pattern).toBe(returned);
    expect(store().steps).toBe(steps);
    expect(store().recipe).toEqual(recipe);
    expect(store().dirty).toBe(false);
    expect(store().history.undo).toHaveLength(0);
    expect(store().previewStep).toBeNull();
    expect(store().runError).toBeNull();
  });

  it('stores an ApiError with its step_index and op', async () => {
    store().setRecipe(recipe);
    vi.mocked(client.runRecipe).mockRejectedValue(new ApiError(400, 'pixelate: boom', { step_index: 0, op: 'pixelate' }));
    await store().runRecipe();
    expect(store().running).toBe(false);
    expect(store().runError).toEqual({ step_index: 0, op: 'pixelate', message: 'pixelate: boom' });
  });

  it('flattens pydantic 422 errors into the message', async () => {
    vi.mocked(client.runRecipe).mockRejectedValue(new ApiError(
      422, [{ loc: ['n_colors'], msg: 'Input should be >= 2' }], { step_index: 1, op: 'quantize_image' },
    ));
    await store().runRecipe();
    expect(store().runError).toEqual({ step_index: 1, op: 'quantize_image', message: 'n_colors: Input should be >= 2' });
  });

  it('a 404 (no input) has no step_index', async () => {
    vi.mocked(client.runRecipe).mockRejectedValue(new ApiError(404, 'design has no input image'));
    await store().runRecipe();
    expect(store().runError).toEqual({ message: 'design has no input image' });
  });
});
