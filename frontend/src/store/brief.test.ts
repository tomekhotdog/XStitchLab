import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import * as client from '@/api/client';
import type { DesignDetail, DesignSummary } from '@/api/types';
import { useEditorStore } from './editorStore';
import { useToast } from './toast';

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  return { ...actual, getDesign: vi.fn(), savePrompt: vi.fn(), saveHistory: vi.fn(), uploadInput: vi.fn() };
});

const summary: DesignSummary = {
  slug: 'riga', title: 'Riga', has_input: true, has_prompt: true, has_pattern: false,
  width: null, height: null, colors: null, stitches: null, thumbnail_png: null,
};

const detail: DesignDetail = { slug: 'riga', title: 'Riga', prompt: 'Draw a house', has_input: false, pattern: null, history: 'Built 1490', version: null };

const store = () => useEditorStore.getState();
const png = () => new File(['x'], 'input.png', { type: 'image/png' });

beforeEach(() => {
  vi.clearAllMocks();
  store().reset();
  useToast.getState().clear();
  useEditorStore.setState({ slug: 'riga' });
});

describe('load', () => {
  it('populates prompt, history and hasInput from the design', async () => {
    vi.mocked(client.getDesign).mockResolvedValue({ ...detail, has_input: true });
    await store().load('riga');
    expect(store().prompt).toBe('Draw a house');
    expect(store().historyText).toBe('Built 1490');
    expect(store().hasInput).toBe(true);
  });
});

describe('savePrompt', () => {
  it('updates prompt with the saved text and toasts', async () => {
    vi.mocked(client.savePrompt).mockResolvedValue({ text: 'New brief' });
    expect(await store().savePrompt('New brief')).toBe(true);
    expect(client.savePrompt).toHaveBeenCalledWith('riga', 'New brief');
    expect(store().prompt).toBe('New brief');
    expect(useToast.getState().message).toBe('Brief saved');
  });

  it('on error toasts and leaves prompt unchanged', async () => {
    useEditorStore.setState({ prompt: 'old' });
    vi.mocked(client.savePrompt).mockRejectedValue(new ApiError(500, 'disk full'));
    expect(await store().savePrompt('new')).toBe(false);
    expect(store().prompt).toBe('old');
    expect(useToast.getState().message).toBe('disk full');
  });
});

describe('saveHistory', () => {
  it('updates history and toasts', async () => {
    vi.mocked(client.saveHistory).mockResolvedValue({ text: 'Rebuilt 1600' });
    expect(await store().saveHistory('Rebuilt 1600')).toBe(true);
    expect(client.saveHistory).toHaveBeenCalledWith('riga', 'Rebuilt 1600');
    expect(store().historyText).toBe('Rebuilt 1600');
    expect(useToast.getState().message).toBe('History saved');
  });
});

describe('uploadInput', () => {
  it('sets hasInput, bumps inputVersion and toasts', async () => {
    vi.mocked(client.uploadInput).mockResolvedValue(summary);
    const before = store().inputVersion;
    const file = png();
    expect(await store().uploadInput(file)).toBe(true);
    expect(client.uploadInput).toHaveBeenCalledWith('riga', file);
    expect(store().hasInput).toBe(true);
    expect(store().inputVersion).toBe(before + 1);
    expect(useToast.getState().message).toBe('Input saved');
  });

  it('on error toasts and changes no state', async () => {
    vi.mocked(client.uploadInput).mockRejectedValue(new ApiError(413, 'too large'));
    const before = store().inputVersion;
    expect(await store().uploadInput(png())).toBe(false);
    expect(store().hasInput).toBe(false);
    expect(store().inputVersion).toBe(before);
    expect(useToast.getState().message).toBe('too large');
  });

  it('ignores a response for a design that is no longer loaded', async () => {
    vi.mocked(client.uploadInput).mockImplementation(async () => {
      useEditorStore.setState({ slug: 'other' });
      return summary;
    });
    expect(await store().uploadInput(png())).toBe(false);
    expect(store().hasInput).toBe(false);
  });
});

describe('panel', () => {
  it('defaults to recipe, switches, and survives load', async () => {
    expect(store().panel).toBe('recipe');
    store().setPanel('brief');
    vi.mocked(client.getDesign).mockResolvedValue(detail);
    await store().load('riga');
    expect(store().panel).toBe('brief');
  });
});
