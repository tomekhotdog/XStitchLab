import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, createDesign, getDesign, listDesigns, pngSrc, runRecipe } from './client';

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  );
  vi.stubGlobal('fetch', fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe('ApiError parsing', () => {
  it('string detail (404)', async () => {
    mockFetch(404, { detail: "design 'nope' not found" });
    const err = await getDesign('nope').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.detail).toBe("design 'nope' not found");
    expect(err.message).toBe("design 'nope' not found");
    expect(err.step_index).toBeUndefined();
    expect(err.op).toBeUndefined();
  });

  it('OpError (400) carries step_index and op', async () => {
    mockFetch(400, { detail: 'pattern op before pixelate', step_index: 0, op: 'background_to_fabric' });
    const err = await runRecipe('x', [{ op: 'background_to_fabric', params: {} }]).catch((e) => e);
    expect(err.status).toBe(400);
    expect(err.detail).toBe('pattern op before pixelate');
    expect(err.step_index).toBe(0);
    expect(err.op).toBe('background_to_fabric');
  });

  it('pydantic 422 keeps the error list as detail', async () => {
    const errors = [{ loc: ['n_colors'], msg: 'Input should be >= 2', type: 'greater_than_equal' }];
    mockFetch(422, { detail: errors, step_index: 1, op: 'quantize_image' });
    const err = await runRecipe('x', []).catch((e) => e);
    expect(err.status).toBe(422);
    expect(err.detail).toEqual(errors);
    expect(err.step_index).toBe(1);
    expect(err.op).toBe('quantize_image');
    expect(err.message).toContain('422');
  });

  it('non-JSON body falls back to the status text', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('boom', { status: 500, statusText: 'Server Error' })));
    const err = await listDesigns().catch((e) => e);
    expect(err.status).toBe(500);
    expect(err.detail).toBe('Server Error');
  });
});

describe('requests', () => {
  it('posts JSON with the right content type and returns the body', async () => {
    const fn = mockFetch(201, { slug: 's', title: 'T', has_input: false });
    const out = await createDesign('s', 'T');
    expect(out.slug).toBe('s');
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/designs');
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify({ slug: 's', title: 'T' }));
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json');
  });

  it('pngSrc adds the data prefix', () => {
    expect(pngSrc('abc=')).toBe('data:image/png;base64,abc=');
  });
});
