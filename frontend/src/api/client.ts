/** One typed function per backend route. Every non-2xx response throws `ApiError`. */

import type {
  DesignDetail, DesignSummary, DmcColour, ExportKind, OpCall, OpSchema, Pattern,
  RunResponse, SheetLayout, ThreadsResponse,
} from './types';

export class ApiError extends Error {
  status: number;
  detail: string | unknown[];
  step_index?: number;
  op?: string;

  constructor(status: number, detail: string | unknown[], extra: { step_index?: number; op?: string } = {}) {
    super(typeof detail === 'string' ? detail : `${status}: validation error`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    if (extra.step_index !== undefined && extra.step_index !== null) this.step_index = extra.step_index;
    if (extra.op !== undefined && extra.op !== null) this.op = extra.op;
  }
}

const BASE = '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(BASE + path, { ...init, headers });
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

async function toApiError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // no JSON body
  }
  if (body && typeof body === 'object' && 'detail' in body) {
    const b = body as { detail: unknown; step_index?: number; op?: string };
    const detail = typeof b.detail === 'string' || Array.isArray(b.detail) ? b.detail : JSON.stringify(b.detail);
    return new ApiError(res.status, detail, { step_index: b.step_index, op: b.op });
  }
  return new ApiError(res.status, res.statusText || `HTTP ${res.status}`);
}

const json = (body: unknown) => JSON.stringify(body);

// --- designs -----------------------------------------------------------------

export const listDesigns = () => request<DesignSummary[]>('/designs');

export const createDesign = (slug: string, title: string) =>
  request<DesignSummary>('/designs', { method: 'POST', body: json({ slug, title }) });

export const getDesign = (slug: string) => request<DesignDetail>(`/designs/${slug}`);

export const inputUrl = (slug: string) => `${BASE}/designs/${slug}/input.png`;

export const uploadInput = (slug: string, file: File | Blob) => {
  const form = new FormData();
  form.append('file', file, file instanceof File ? file.name : 'input.png');
  return request<DesignSummary>(`/designs/${slug}/input`, { method: 'PUT', body: form });
};

export const savePrompt = (slug: string, text: string) =>
  request<{ text: string }>(`/designs/${slug}/prompt`, { method: 'PUT', body: json({ text }) });

export const saveHistory = (slug: string, text: string) =>
  request<{ text: string }>(`/designs/${slug}/history`, { method: 'PUT', body: json({ text }) });

export const savePattern = async (slug: string, pattern: Pattern) =>
  (await request<{ pattern: Pattern }>(`/designs/${slug}`, { method: 'PUT', body: json({ pattern }) })).pattern;

export const runRecipe = (slug: string, recipe: OpCall[]) =>
  request<RunResponse>(`/designs/${slug}/run`, { method: 'POST', body: json({ recipe }) });

export const exportUrl = (slug: string, kind: ExportKind, layout?: SheetLayout) =>
  `${BASE}/designs/${slug}/export/${kind}${layout ? `?layout=${layout}` : ''}`;

export const threads = (slug: string) => request<ThreadsResponse>(`/designs/${slug}/threads`);

// --- ops and reference data --------------------------------------------------

export const applyOp = async (pattern: Pattern, op: string, params: Record<string, unknown> = {}) =>
  (await request<{ pattern: Pattern }>('/ops/apply', { method: 'POST', body: json({ pattern, op, params }) })).pattern;

export const listOps = () => request<OpSchema[]>('/ops');

export const defaultRecipes = () => request<Record<string, OpCall[]>>('/recipes/defaults');

export const listDmc = () => request<DmcColour[]>('/dmc');

export const promptTemplate = async () => (await request<{ text: string }>('/prompt-template')).text;

// --- helpers -----------------------------------------------------------------

/** A raw base64 PNG from the API as an <img src>. */
export const pngSrc = (b64: string) => `data:image/png;base64,${b64}`;
